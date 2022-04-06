from src.banrural_bank_gt import models 
import datetime
from bank_base_gt import UserPasswordBankLogin

credentials = UserPasswordBankLogin(username="9093776", password="Gh4Y9LcH77")


with models.BanruralCorporateBank(credentials) as connection:
    accounts = connection.fetch_accounts()
    for a in accounts:
        print(a)
        
        mov = a.fetch_movements(
            datetime.date.today() - datetime.timedelta(days=60),
            datetime.date.today() + datetime.timedelta(days=1),
        )
        print(mov)
        # for m in mov:
        #     print(m)
                
