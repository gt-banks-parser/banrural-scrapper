# Banrural Scrapper

Python library to scrap Banrural Website

The intended use of this library is to make it easy to access Banrural bank data to allow the automatisation of processes that currently banks doesn't allow.


## How to use it

### Installation

`pip install banrural-scrapper-gt`

If you are using requirements.txt just add `banrural-scrapper-gt` into the file


### Usage

#### Precautions

- Don't access to Banrural website or mobile app while executing some script usign this library.
- Login with the library will fail if you are logged in from the website or mobile app.

#### Login

The recommended method for login is using `with` statement of Python. We initialize the class in the with and will make automatically login with the provided credentials and will logout after finishing all the work and if some exception happens we ensure that logout method is called.

```python
from banrural_bank_gt import BanruralBank, UserPasswordBankLogin

credentials = UserPasswordBankLogin(username="ENTER YOUR USERNAME", password="ENTER YOUR PASSWORD")
with BanruralBank(credentials) as connection:
    # Do your work here

# We are logout now
```

#### Get accounts

```python
from banrural_bank_gt import BanruralBank, UserPasswordBankLogin

credentials = UserPasswordBankLogin(username="ENTER YOUR USERNAME", password="ENTER YOUR PASSWORD")
with BanruralBank(credentials) as connection:
    accounts = connection.fetch_accounts() # Fetch all accounts
        for a in accounts:
            print(a)

```

#### Get movements

We can retrieve the movements of an account using `fetch_movements` method in `BanruralBankAccount`

```python
import datetime
from banrural_bank_gt import BanruralBank, UserPasswordBankLogin
credentials = UserPasswordBankLogin(username="ENTER YOUR USERNAME", password="ENTER YOUR PASSWORD")

with BanruralBank(credentials) as connection:
    accounts = connection.fetch_accounts()
    for a in accounts:
        mov = a.fetch_movements(
            datetime.date.today() - datetime.timedelta(days=60),
            datetime.date.today() + datetime.timedelta(days=1),
        )
        for m in mov:
            print(m)
```


#### Logout

It's important to logout after you finish your operations otherwise you can lock yourself and that won't allow you to login from the website, that's due security protections of Banrural.

Even though `with` statement is the recommended way to make sure logout method is called. You can also execute it manually.

```python
    bank = BanruralBank(credentials)
    try:
        bank.login()
        # Do your work
    except:
        pass
    finally:
        bank.logout()
```

### Contributing

1. Fork it
2. Create your feature branch
3. Commit your changes
4. Push your branch
5. Create a pull request

### FAQ

- Why I need to enter my credentials? It is safe?
    - We need your credentials to authenticate in the bank, those credentials are not stored in any place. This is open source library so you can check the code.
- Can you make some program for me using this library? 
    - Of course, this library provides a base for another utilities and potentially any thing that is on the website of banrural is under subject for automatization, if you need some customization or build a program on top of this library please contact me at dev at csimon (dot) dev and I will be happy to help you.