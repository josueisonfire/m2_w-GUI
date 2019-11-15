import pymongo

myclient = pymongo.MongoClient("mongodb://localhost:27017/")
mydb = myclient["test_database"]
mycol = mydb["toddler"]

mycol.drop() 

mycol = mydb["items"]

mycol.drop() 
