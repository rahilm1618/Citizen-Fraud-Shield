import asyncio
import sys

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models import ScamPattern
from app.services.embedding_service import get_embedding
from app.config import settings

SCAM_DATA = [
    # CBI/ED Digital Arrest
    {
        "title": "CBI Digital Arrest - Aadhaar misuse",
        "category": "digital_arrest",
        "source": "Seed Data",
        "script_text": "I am Inspector Sharma calling from the Central Bureau of Investigation, Mumbai branch. Your Aadhaar number 1234-5678-9012 has been found linked to a money laundering case involving hawala transactions. We have issued a digital arrest warrant against you. You must stay on this Skype video call and not disconnect, or we will dispatch officers to your location. You need to transfer Rs 50,000 as a refundable security deposit to a verified RBI holding account to clear your name."
    },
    {
        "title": "ED Skype Interrogation",
        "category": "digital_arrest",
        "source": "Seed Data",
        "script_text": "This is Enforcement Directorate. We have intercepted a parcel containing illegal passports and drugs under your name. You are currently under digital arrest. Download Skype immediately and join the ID 'ED-Cyber-Cell'. Do not inform your family. We need you to verify your bank balances and transfer funds to a safe government account for auditing purposes."
    },
    {
        "title": "Police Cyber Cell Threat",
        "category": "digital_arrest",
        "source": "Seed Data",
        "script_text": "Hello, cyber crime branch Delhi here. Your bank account is flagged for funding terrorism. We are freezing all your accounts. To avoid immediate physical arrest, you must comply with our virtual investigation. Please send your entire savings to the secret police account 9876543210 at HDFC bank. It will be returned in 24 hours once verified."
    },
    
    # Customs/FedEx Parcel
    {
        "title": "FedEx Customs Seizure",
        "category": "customs_scam",
        "source": "Seed Data",
        "script_text": "This is an automated call from FedEx. Your parcel bound for Taiwan has been seized by customs because it contains 5 unauthorized credit cards and 200 grams of MDMA. Press 1 to speak with a customs officer. ... Hello, I am Officer Verma. To avoid legal action, you must pay a customs clearance penalty of Rs 85,000 via UPI immediately."
    },
    {
        "title": "DHL Fake Parcel Notice",
        "category": "customs_scam",
        "source": "Seed Data",
        "script_text": "Sir, this is DHL customer care. A package sent by you to London has been stopped by customs. They found illegal narcotics inside. The police have been notified. We can settle this if you pay the customs fine of Rs 1,50,000 right now. Otherwise, the police will arrive at your home address in 30 minutes."
    },
    {
        "title": "Customs Duty Gift Scam",
        "category": "customs_scam",
        "source": "Seed Data",
        "script_text": "Hi, I am an officer at Delhi Airport Customs. A friend of yours from the UK has sent a luxury gift parcel containing an iPhone and gold jewelry, but it is stuck at customs. You need to pay Rs 25,000 as customs duty charge to release it. Please transfer the amount to this UPI ID: customs.delhi@sbi"
    },

    # Electricity Disconnection (User Requested)
    {
        "title": "Electricity Disconnection SMS",
        "category": "electricity_scam",
        "source": "Seed Data",
        "script_text": "Dear Customer, your electricity power will be disconnected tonight at 9:30 PM from electricity office because your previous month bill was not updated. Please immediately contact our electricity officer on 9876543210. Download AnyDesk app so they can help you pay the pending Rs 15 charge."
    },
    {
        "title": "Power Cut Threat Phone Call",
        "category": "electricity_scam",
        "source": "Seed Data",
        "script_text": "Hello, I am calling from the state electricity board. Your bill payment failed to update in our system. We are sending a lineman to cut your power connection in 15 minutes. To stop this, please pay the Rs 52 update fee through this link we are sending you on WhatsApp. Please share your screen so I can guide you."
    },
    {
        "title": "BSES Bill Pending SMS",
        "category": "electricity_scam",
        "source": "Seed Data",
        "script_text": "BSES Alert: Dear Consumer, power will be disconnected at 10:00 PM today due to non-payment. Call customer support at 8888888888. Do a test transaction of Rs 10 using the TeamViewer QuickSupport app to update the bill desk."
    },

    # Work-From-Home Scam (User Requested)
    {
        "title": "YouTube Like/Subscribe Job",
        "category": "work_from_home",
        "source": "Seed Data",
        "script_text": "Hello, we are offering a part-time work from home job. You just need to like and subscribe to YouTube videos to earn Rs 3000 to 5000 daily. For the first task, like these 3 videos and send a screenshot. Great, now to receive your salary, please register on our VIP merchant portal and pay a small activation fee of Rs 2000."
    },
    {
        "title": "Google Maps Review Job",
        "category": "work_from_home",
        "source": "Seed Data",
        "script_text": "Hi, I am an HR recruiter. We have a WFH opportunity where you review hotels on Google Maps and earn money. We will pay you Rs 150 per review. To proceed to the premium high-paying tasks, you need to invest Rs 10,000 in our cryptocurrency portal which will yield a 40% return by tonight."
    },
    {
        "title": "Data Entry Pre-Paid Task",
        "category": "work_from_home",
        "source": "Seed Data",
        "script_text": "Welcome to our data entry platform. We provide captcha typing jobs. But first, your account is locked. You must complete a 'pre-paid task' to unlock it. Send Rs 5000 to this UPI ID, and you will immediately get back Rs 7000. It is a mandatory step to verify your bank account for salary deposits."
    },

    # Loan Fraud
    {
        "title": "Instant Loan App Harassment",
        "category": "loan_fraud",
        "source": "Seed Data",
        "script_text": "You took a loan of Rs 5000 from our app 7 days ago. The repayment amount is now Rs 15,000 due to late fees. If you do not pay immediately, we have access to your contacts and gallery. We will morph your photos and send them to your family and friends calling you a thief and a rapist."
    },
    {
        "title": "Fake Loan Approval Fee",
        "category": "loan_fraud",
        "source": "Seed Data",
        "script_text": "Congratulations! Your personal loan of Rs 5,00,000 has been approved by Bajaj Finance. However, your CIBIL score is low. To disburse the amount, you must pay a processing and insurance fee of Rs 12,500 upfront. Please transfer this to our manager's personal account to expedite the process."
    },

    # KYC Update / Bank Fraud
    {
        "title": "PAN Card Blocked SMS",
        "category": "kyc_fraud",
        "source": "Seed Data",
        "script_text": "Dear SBI User, your YONO account will be blocked today because your PAN card is not updated. Click here http://sbi-kyc-update-portal.info to update PAN immediately. Do not share the OTP with anyone."
    },
    {
        "title": "Credit Card Limit Increase",
        "category": "kyc_fraud",
        "source": "Seed Data",
        "script_text": "Hello sir, I am calling from ICICI credit card department. You are eligible for a free lifetime credit card upgrade and limit increase to Rs 8 Lakhs. I just need to verify your details. Please tell me your 16-digit card number, expiry date, and the CVV on the back. Now, tell me the OTP you just received to confirm."
    },
    {
        "title": "Sim Card KYC Warning",
        "category": "kyc_fraud",
        "source": "Seed Data",
        "script_text": "Jio Alert: Your SIM card will be deactivated in 24 hours pending e-KYC verification. Call customer care at 9999999999. Download the APK file sent on WhatsApp and install it to complete video KYC."
    },

    # Lottery / Prize Scam
    {
        "title": "KBC Jio Lottery Winner",
        "category": "lottery_scam",
        "source": "Seed Data",
        "script_text": "Congratulations! You have won the Kaun Banega Crorepati and Jio joint lottery of Rs 25 Lakhs. Your mobile number was selected in a lucky draw. To claim the prize money, you must pay the government tax and bank processing fee of Rs 25,000. Do not tell anyone about this until you receive the money, as it is highly confidential."
    },
    {
        "title": "WhatsApp Lucky Draw",
        "category": "lottery_scam",
        "source": "Seed Data",
        "script_text": "Dear WhatsApp user, your number has won the international lucky draw prize of $50,000. Please contact our manager in the UK via this WhatsApp number to claim. You will need to send a customs clearance fee via Western Union."
    },

    # Stock Market / Investment
    {
        "title": "WhatsApp Stock Tips Group",
        "category": "investment_scam",
        "source": "Seed Data",
        "script_text": "Join our VIP Stock Market Tips WhatsApp group. Our expert sir gives 300% guaranteed returns on penny stocks. Download our proprietary trading app from this APK link. Deposit your money directly into the app. When you try to withdraw, you will have to pay 20% tax before withdrawal is allowed."
    },
    {
        "title": "Crypto High Yield Scam",
        "category": "investment_scam",
        "source": "Seed Data",
        "script_text": "Invest in our cloud mining cryptocurrency platform. Put in Rs 50,000 today and you will receive Rs 5000 daily for the next 100 days. Refer friends to get a 10% bonus. Transfer funds to this Binance wallet address."
    },

    # Sextortion
    {
        "title": "Video Call Sextortion",
        "category": "sextortion",
        "source": "Seed Data",
        "script_text": "We recorded your WhatsApp video call. We have the inappropriate video. If you do not transfer Rs 50,000 right now, we will upload this video to YouTube and send the link to all your Facebook friends and family members. Pay up immediately or your life will be ruined."
    },
    {
        "title": "Fake Police Sextortion",
        "category": "sextortion",
        "source": "Seed Data",
        "script_text": "Hello, I am Inspector Singh from Delhi Cyber Police. We have arrested a girl who claims you were involved in illegal video chats. She attempted suicide. You are now a suspect. To settle this out of court and remove your name from the FIR, you must pay a fine of Rs 1 Lakh."
    },

    # Fake RBI / Government Notice
    {
        "title": "RBI Account Freeze Notice",
        "category": "government_impersonation",
        "source": "Seed Data",
        "script_text": "This is an official communication from the Reserve Bank of India. Your bank accounts have been frozen due to suspicious international transactions. You must pay a penalty of Rs 15,000 to the RBI clearance account to unfreeze them. Failure to do so will result in a 5-year jail term."
    },
    {
        "title": "Income Tax Refund SMS",
        "category": "government_impersonation",
        "source": "Seed Data",
        "script_text": "Important Alert from Income Tax Department. A refund of Rs 12,450 has been approved for your PAN card. Please click the link to verify your bank account details and claim the refund immediately before it expires today."
    },
    
    # Extra Generic Scams
    {
        "title": "OLX Army Officer Scam",
        "category": "classifieds_scam",
        "source": "Seed Data",
        "script_text": "I saw your listing for the sofa on OLX. I am an Army officer currently posted in Kashmir. I will buy it. I am sending you Rs 5 via Google Pay to test the connection. ... Okay, now to receive the full Rs 10,000, please scan the QR code I am sending you and enter your UPI PIN."
    },
    {
        "title": "Relative in Distress",
        "category": "impersonation",
        "source": "Seed Data",
        "script_text": "Hello Uncle, it's me. I am in the hospital. I had an accident and need money urgently for the operation. Please don't tell my parents, they will worry. Can you transfer Rs 40,000 to this doctor's account right now? I will return it tomorrow."
    },
    {
        "title": "Wrong Number Scam",
        "category": "impersonation",
        "source": "Seed Data",
        "script_text": "Oh sorry, I dialed the wrong number. By the way, your voice sounds very nice. Can we be friends? Let's chat on WhatsApp... (few days later) I have sent you a gift from London but it is stuck at customs, please pay the fee."
    },
    {
        "title": "Customer Care Refund Scam",
        "category": "impersonation",
        "source": "Seed Data",
        "script_text": "Hello, I am calling from Swiggy/Zomato customer care. We noticed your order was delayed and you asked for a refund on Twitter. To process the refund of Rs 350, please download the AnyDesk app and tell us the 9-digit code."
    },
    # Romance/Matrimonial Scam (slow-burn, structurally different from urgent-threat scripts)
    {
        "title": "Matrimonial Site Overseas Groom",
        "category": "romance_scam",
        "source": "Seed Data",
        "script_text": "Hello my dear, I am so happy we matched on the matrimonial site. I am currently working as a doctor with the UN in Syria, but I will be coming to India next month to meet your family. I have a gift and some savings I want to bring for our future, around $80,000, but I need help paying the courier and diplomatic clearance fee of Rs 45,000 to release it from customs. Please help me, I trust only you."
    },
    {
        "title": "Instagram Army Officer Romance",
        "category": "romance_scam",
        "source": "Seed Data",
        "script_text": "Hi, I saw your profile and felt an instant connection. I am a Colonel posted at the border, it gets lonely here. I want to send you a parcel with gifts and my pension savings before I retire next year. Please don't mention this to anyone, keep it between us. The courier company is asking for a security deposit of Rs 30,000 to dispatch the box, can you pay it and I will return double when we meet."

    },

    # Tech Support Scam (distinct from bank-related AnyDesk scripts already present)
    {
        "title": "Fake Microsoft Virus Alert",
        "category": "tech_support_scam",
        "source": "Seed Data",
        "script_text": "This is an automated security alert from Microsoft. Your computer has been infected with a dangerous virus and hackers are currently stealing your banking information. Please call our toll-free support number immediately. ... Hello sir, I am a certified Microsoft technician. I need you to download AnyDesk right now so I can remove the virus remotely. Please do not turn off your computer during this process."
    },
    {
        "title": "Amazon Account Compromise Call",
        "category": "tech_support_scam",
        "source": "Seed Data",
        "script_text": "Hello, this is Amazon security department. We have detected an unauthorized purchase of Rs 89,999 for an iPhone from your account in a different city. If this was not you, press 1 to speak with our fraud prevention officer. ... To cancel this order and secure your account, I need you to install our secure remote verification tool and share the OTP sent to your phone."
    },

    # Pure OTP-theft scam (short, distinct mechanism from KYC scripts)
    {
        "title": "Wrong Transaction OTP Scam",
        "category": "otp_theft",
        "source": "Seed Data",
        "script_text": "Sir, I accidentally transferred Rs 25,000 to your account instead of my vendor's account. This was a mistake, please help me reverse it. You will receive an OTP on your phone in a moment, that is the cancellation code. Please read it out to me quickly so I can cancel the wrongly sent transaction before it processes."
    },
    {
        "title": "Cashback Offer OTP Scam",
        "category": "otp_theft",
        "source": "Seed Data",
        "script_text": "Congratulations, you are eligible for a Paytm cashback of Rs 500 for being a loyal customer. To credit this cashback instantly to your wallet, I just need you to confirm the 6-digit verification code that was just sent to your registered mobile number."
    },

    # Fake Insurance/Policy Matured Scam
    {
        "title": "LIC Policy Maturity Fee",
        "category": "insurance_scam",
        "source": "Seed Data",
        "script_text": "Good news, your LIC policy from 2015 has matured and a maturity amount of Rs 2,45,000 is ready for disbursement. However, due to a new government regulation, you need to pay a one-time GST and processing charge of Rs 8,500 before the amount can be released to your bank account. Please pay today as the disbursement window closes tonight."
    },

    # Fake Job Offer / Interview Letter Scam (distinct from task-based work-from-home scripts)
    {
        "title": "Fake HR Selection Letter",
        "category": "job_offer_scam",
        "source": "Seed Data",
        "script_text": "Congratulations, you have been shortlisted for the Assistant Manager position at our company with a starting salary of Rs 45,000 per month. To confirm your joining and receive your official offer letter and employee ID, please pay a refundable security deposit of Rs 3,500 for laptop and ID card issuance within the next 2 hours, as the vacancy is limited."
    },

    # Second classifieds_scam entry (bulking up thin category)
    {
        "title": "OLX Buyer Advance Payment Scam",
        "category": "classifieds_scam",
        "source": "Seed Data",
        "script_text": "Hi, I am interested in your bike listed on OLX. I am a defense personnel and cannot come in person right now, but I will pay through a courier partner. I am sending an advance of Rs 2,000 via a payment link, please click it to receive the money. Actually the link isn't working, can you also share the OTP you received so I can resend the payment properly."
    }
]

async def seed():
    print(f"Connecting to database: {settings.database_url}")
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )

    async with async_session() as session:
        # Check if we already have data to avoid duplicates on multiple runs
        from sqlalchemy import select
        result = await session.execute(select(ScamPattern.title))
        existing_titles = {row[0] for row in result.all()}

        print(f"Generating embeddings and inserting scam patterns...")
        for idx, item in enumerate(SCAM_DATA):
            if item["title"] in existing_titles:
                continue
            # Generate embedding
            print(f"[{idx+1}/{len(SCAM_DATA)}] Embedding: {item['title']}")
            emb = await get_embedding(item["script_text"])
            
            pattern = ScamPattern(
                title=item["title"],
                category=item["category"],
                source=item["source"],
                script_text=item["script_text"],
                embedding=emb
            )
            session.add(pattern)
        
        await session.commit()
        print("✅ Successfully seeded scam patterns.")

    # Create the HNSW or IVFFlat index since we now have data
    # For small datasets, exact search is fine, but since schema dictates it, 
    # we can create an index. However, IVFFlat requires some data.
    # We will just execute the CREATE INDEX statement.
    async with engine.begin() as conn:
        from sqlalchemy import text
        try:
            print("Creating ivfflat index on scam_patterns...")
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_scam_patterns_embedding ON scam_patterns USING ivfflat (embedding vector_cosine_ops) WITH (lists = 1)"))
            print("✅ Index created.")
        except Exception as e:
            print(f"Note: Index creation failed (maybe not enough rows for ivfflat), but that's okay for dev: {e}")

    await engine.dispose()

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(seed())
