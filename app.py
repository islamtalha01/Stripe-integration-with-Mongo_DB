from flask import Flask, render_template, request, jsonify
import stripe
import os
from flask_cors import CORS 
from pymongo import MongoClient
app = Flask(__name__)
client = MongoClient('localhost', 27017)  # Connecting to the local instance of MongoDB
db = client['stripe_db']  # Choose a database (will be created if doesn't exist)
users = db['users']  # Choose a collection (similar to a table in relational databases)
from pymongo import MongoClient, errors

try:
    # Attempt to establish a connection
    client = MongoClient('localhost', 27017, serverSelectionTimeoutMS=5000)  # Adding a timeout for connection
    client.server_info()  # Will throw an exception if not connected

    # If connected, select database and collection
    db = client['stripe_db']
    users = db['users']

    # Print the count of documents in the 'users' collection
    print(f"Connected successfully. 'users' collection has {users.count_documents({})} documents.")

except errors.ServerSelectionTimeoutError as err:
    # If connection attempt times out
    print("Could not connect to MongoDB:", err)
except Exception as e:
    print("An error occurred:", e)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Stripe configuration
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

secret_endpoint_key=os.getenv('STRIPE_ENDPOINT_SECRET') 

@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    try:
        # Get the product_id (plan_id) from the request body or form data
        product_id = request.json.get('product_id')

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': product_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url='https://example.com/success',  # temporary URL
            cancel_url='https://example.com/cancel',    # temporary URL
        )
        print("Checkout session created successfully!")
        print(checkout_session.id)  # Console message
        return jsonify(id=checkout_session.id)
    except Exception as e:
        print(f"Error creating checkout session: {str(e)}")  # Console message
        return jsonify(error=str(e)), 403
    

@app.route('/test_webhook', methods=['POST'])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        # Check the webhook's signature to ensure its authenticity
        event = stripe.Webhook.construct_event(
            payload, sig_header, secret_endpoint_key
        )
    except ValueError as e:
        # Invalid payload
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return jsonify({'error': 'Invalid signature'}), 400

    # Handle the `customer.subscription.created` event
    if event.type == 'customer.subscription.created':
        subscription = event.data.object
        print(subscription)
        cus_id=subscription.get("customer")
        plan_id = subscription['plan']['id']
        customer = stripe.Customer.retrieve(cus_id)
        name = customer["name"]
        email = customer["email"]
        discord_Id=  customer["metadata"]["discord_id"]
        plan = stripe.Plan.retrieve(plan_id)    
        print(name,email,discord_Id,plan_id,plan)
        #Insert into MongoDB
        try:
            users.insert_one({
            "name": name,
            "email": email,
            "subscription_plan_id": plan_id,
            "discord_id": discord_Id,
            "subscription_status": "active",
            "stripe_customer_id": cus_id
        })
        except Exception as e:
         print(f"Error inserting into database: {e}")
       

    # Handle the `customer.subscription.updated` event

    elif event.type == 'customer.subscription.updated':
        subscription = event.data.object
        cus_id = subscription.get("customer")
        plan_id = subscription['plan']['id']
        customer = stripe.Customer.retrieve(cus_id)
        name = customer["name"]
        email = customer["email"]
        discord_Id = customer["metadata"]["discord_id"]
        
        # Fetch the existing plan ID from MongoDB for this user
        existing_user = users.find_one({"stripe_customer_id": cus_id})
    
    # If the user is not found in MongoDB or the user's plan ID differs from the updated plan ID
        if (existing_user.get("subscription_plan_id") != subscription['plan']['id']):
         plan_id = subscription['plan']['id']

        # Update the plan ID in MongoDB
         users.update_one({"stripe_customer_id": cus_id}, {"$set": {"subscription_plan_id": plan_id}})

    # Handle the `customer.subscription.deleted` event
    elif event.type == 'customer.subscription.deleted':
        cus_id = subscription.get("customer")

        # Mark the subscription as "cancelled" in MongoDB
        users.update_one({"stripe_customer_id": cus_id}, {"$set": {"subscription_status": "cancelled"}})
        #anyaddtional code to make user aware theat subscription has beedn canceled
    elif event.type == 'customer.subscription.resumed':
    # When the subscription is resumed
     subscription = event.data.object
     cus_id = subscription.get("customer")

    # Update the MongoDB entry to reflect the active status
     users.update_one({"stripe_customer_id": cus_id}, {"$set": {"subscription_status": "active"}})

    elif event.type == 'customer.subscription.paused':
    # When the subscription is paused
     subscription = event.data.object
     cus_id = subscription.get("customer")

    # Update the MongoDB entry to reflect the paused status
     users.update_one({"stripe_customer_id": cus_id}, {"$set": {"subscription_status": "paused"}})
    

    return jsonify({'status': 'success'}), 200






 
        

    return jsonify({'status': 'success'}), 200

 



if __name__ == "__main__":
    CORS(app)
    app.run(debug=True)
