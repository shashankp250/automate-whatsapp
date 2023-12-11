from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from pymongo import MongoClient
from datetime import datetime
import re
import time

cluster = MongoClient(
    "mongodb+srv://shashankp250:UzJKWmzgvFCWhjxt@cluster0.xc7kyic.mongodb.net/?retryWrites=true&w=majority")
db = cluster["decimas_finance"]
users = db["users"]
applications = db["applications"]

app = Flask(__name__)


def is_valid_pan(pan):
    # PAN format: First five characters are letters, next four are numbers, & the last character is a letter
    pattern = re.compile(r'^[A-Za-z]{5}[0-9]{4}[A-Za-z]$', re.IGNORECASE)
    return bool(pattern.match(pan))


@app.route("/", methods=['GET', 'POST'])
def reply():
    # getting user input text and phone number
    text = request.form.get("Body")
    number = request.form.get("From")
    if number:
        number = number.replace("whatsapp:", "")

    response = MessagingResponse()
    user = users.find_one({"number": number})

    if not bool(user):
        response.message(
            "👋 Hi, Greetings!! 🎓\n\n🌟 Welcome to *CredKnow* Avail hassle-free education loans with just a few simple steps. "
            "We offer a 3% annual interest rate with zero processing fees. 🌟 \n\nWould you like to apply for an education loan? "
            "Choose an option from below \n\n*Type*\n\n1️⃣For YES \n2️⃣For NO")
        users.insert_one({"number": number, "status": "main", "messages": []})
    elif user["status"] == "main":
        try:
            option = int(text)
        except:
            response.message("Please enter valid response")
            return str(response)

        if option == 1:
            response.message(
                "🔍 Excellent! To proceed, we need your PAN number for verification purposes. \nPlease provide your PAN number.")
            users.update_one({"number": number}, {"$set": {"status": "pan_verification"}})
        elif option == 2:
            response.message("Thank you for reaching out. Have a good day.")
            users.update_one({"number": number}, {"$set": {"status": "main"}})
        else:
            response.message("Please enter valid response")
            return str(response)
    elif user["status"] == "pan_verification":
        if is_valid_pan(text):
            response.message(f"Hold On ⌛️ We are validating your PAN {text} details...")
            time.sleep(1)
            response.message("🔒 Your PAN details have been validated successfully!"
                             "\nTo proceed further, please provide electronic consent by replying with *YES* to validate your *AADHAR* details.")
            # update status and pan num
            users.update_one({"number": number}, {"$set": {"status": "aadhar_econsent"}})
            users.update_one({"number": number}, {"$set": {"pan_number": text}})

        else:
            response.message("Please enter valid PAN number")
            return str(response)
    elif user["status"] == "aadhar_econsent":
        if not text.isdigit() and text.lower() == "yes":
            response.message("Alright 🙂, Your 📋 consent has been received! An application ID has been generated for you: [Application ID].")
            response.message("We'll now assess your CIBIL report. This may take a moment...⌛️")
            time.sleep(1)
            response.message("🎉 Congratulations! Your loan has been approved based on your CIBIL report! \n\n We would need few more details.")
            response.message("What is your *source of income* ? Please select an option below \n\n*Type*\n\n1️⃣ For Business\n2️⃣ For Salary\n3️⃣ Rental\n4️⃣ Others")
            users.update_one({"number": number}, {"$set": {"status": "onboarding-step1"}})
        elif not text.isdigit() and text.lower() == "no":
            response.message("Uh oh!!☹️ EConsent is mandatory in order to process your application further. ")
            response.message("To proceed further, please provide electronic consent by replying with *YES* to validate your *AADHAR* details.")
        else:
            response.message("Please enter valid response")
            return str(response)
    elif user["status"] == "onboarding-step1":
        try:
            option = int(text)
        except:
            response.message("Please enter valid response")
            return str(response)

        if 1 <= option <= 4:
            sources = ["Business", "Salary", "Rental", "Others"]
            selected = sources[option - 1]
            users.update_one({"number": number}, {"$set": {"income_source": selected}})
            users.update_one({"number": number}, {"$set": {"status": "onboarding-step2"}})
            response.message("Almost there!! , Kindly mention your *monthly income* 💵?")
        else:
            response.message("Please select valid option between 1-4")
            return str(response)
    elif user["status"] == "onboarding-step2":
        try:
            income = float(text)
            if 1000 <= income <= 1000000:
                msg = response.message("Please find your attached sanction letter. Thank you for choosing *CredKnow*! 😎")
                msg.media("https://www.apagrisnet.gov.in/pdf/PACS/sanction%20letter.docx.pdf")
                users.update_one({"number": number}, {"$set": {"monthly_income": income}})
                users.update_one({"number": number}, {"$set": {"status": "sanctioned"}})
            else:
                response.message("Income should be in between 1000 and 1000000 in order to avail the loan.")
                return str(response)
        except ValueError:
            response.message("Please enter valid income.")
            return str(response)

    users.update_one({"number": number}, {"$push": {"messages": {"text": text, "date": datetime.now()}}})
    return str(response)


if __name__ == "__main__":
    app.run()
