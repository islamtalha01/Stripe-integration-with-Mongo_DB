# Stripe-integration-with-Mongo_DB
You can So stripe needs to send to the backend a notification when there are some changes on subscriptions so that the backend can update the mongoDB, our backend is in flask.
 Backend will handle:

- When a new user start a subscription, gets the name, mail, plan name, and discord id (a custom filed) and Store in the DB.

- When a user update their subscription (change the plan), get the new plan name and user details and Store into DB.

- When a user stop their subscription then status will be Changed to Pause in The DB

- When a user re start their subscription there Status will  be updated as Active User

Just Setup the Environment Variable STRIPE_API_KEY and Webhook endpoint SECRET_KEY
