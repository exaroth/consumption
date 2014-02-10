# Consumption

Consumption is an asynchronous JSON API written in Python using
Tornado web server and SQLAlchemy, it is meant to be used along with 
JavaScript via AJAX calls. It provides easy to use interface for fetching given query and
nicely parses JSON response.


### Installation


NOTE: requires Virtualenv and pip

To install:

``` shell
pip install virtualenv
//if not installed
git clone https://github.com/exaroth/consumption.git
virtualenv create consumption
cd consumption
source bin/activate
pip install -r requirements.txt
```

First set database connection in core/config.py
it uses SQLite database by default

Next create db:

``` shell
python create_db.py
```

to run test server simply:

``` python

python run.py --port=6000
```

port defaults to 8000 if not set

### Usage

Consumption provides easy to use client for fetching data from the server
to access it simply enter base localhost with port number eg.localhost:8000

There you can set address query string along with body and method of the request.
By default Consumption doesnt check headers for XMLHttpRequest so normal http calls work aswell.
To change it uncomment proper lines in views.py

### Sample Request adresses

#### User Interaction

Consumption provides 2 base adresses for interacting with user accounts:

##### /users 


    -- GET method fetches a list of users
	also you can set up limit and offset for easy pagination
	example query:
	:: /users?limit=10&offset=15
	also returns _metadata object containing current offset limit and total number of users



   -- POST creates new user requires properly parsed JSON file eg.
   ``` json
	{
	"users": {
	"username": "konrad",
	"password": "test",
	"email": "konrad@gmail.com"
	}
} 
``` json
-- behind the scenes it hashes the password, creates unique user_uuid key, checks for uniqueness and parses input values -- Returns code 201 if succesful

##### /user


--GET - get single user information, by default it uses uuid to check for match
	 - this can be changed by providing direct=0 parameter in query,
	 aswell as password value, if username and password are verified returns 
	 detailed user info
	 sample request:
	 /user?id=konrad&direct=0 -- returns globally visible info
	 /user?id=konrad&password=test&direct=0 -- returns detailed info
	 /user?id=16fd2706-8baf-433b-82eb-8c7fada847da -- gets user by uuid


--PUT - updates user information requires proper username and password in query string 
along with data to update (this should be changed tbh), body JSON file shoucl look
along with this lines:
query /user?username=x&password=y
``` json
{
	"update": {
		"password": "changed",
		"email": "changed@changed.com"
	}
}
```
Only fields specified in CUSTOM_USER_FIELDS can be changed
returns code 201 if succesfull


-- DELETE -- deletes the user requires only proper username and password,
sample query : /user?id=x&password=y

#### Product Interaction

##### /products
 -- similarly to /users implements methods for creating new product and getting product list


 -- GET -- returns product list with given limit and offser -- sample query:
 	/products -- returns first 10 items
 	/products?limit=10&offset=20 -- limits to 10 and offset 20



 --POST -- creates a new product, only users with existing account can do that
 		requires JSON file containing:


``` json
{
"user": {
	"username": "konrad",
	"password": "test"
},
"product": {
	"product_name": "wiertarka",
	"product_desc": "wrrumm",
	"category": "narzedzia" -- optional defaults to "Other",
	"price": "String containing price"
}
}
```
		return 201 if created

##### /product -- same as users allows getting product info, updating and deleting

sample queries :


GET -- 	/product?id=wiertarka&direct=1	


PUT -- /product , JSON: 


``` json
{
"update": {
"product_name": "wiertarka" -- required even though cannot be changed,
"product_desc": "changed"
},
"user": {
"username": "konrad",
"password": "test"
}
}
``` 

DELETE -- /product?id=wierarka&name=konrad&password=test&direct=0
if direct == 0 get product by uuid



#### Buying Products

Consumption also implements basic buying functionality 

##### /products/buy


Buy an item with given quantity
it requires following JSON file:

``` json
{
"user": {
"user_uuid": "16fd2706-8baf-433b-82eb-8c7fada847da",
"username": "konrad" -- of not provided looks by uuid,
"password": "test"
},
"product": {
"product_uuid": "16fd2706-8baf-433b-82eb-8c7fada847da",
"product_name": "wiertarka", -- if not provided gets it by uuid
"quantity": 10
}
}
```

Only reqistered users can buy products
returns code 201 if succesfull

Also you can see which products an user has bought:
##### /user/<username>/bought

Fetches all products bought by user with given username

##### products/top 

Returns list of most bought products






