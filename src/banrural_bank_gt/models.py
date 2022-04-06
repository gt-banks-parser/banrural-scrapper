import datetime
import logging
import math
import operator
import random
import string
import sys
from functools import reduce
from urllib.parse import parse_qs, urlencode
import time
from bank_base_gt import (
    AbstractBankAccount,
    Bank,
    BaseBank,
    InvalidCredentialsException,
    Movement,
)
from bank_base_gt.bank import ChangePasswordRequired
from bs4 import BeautifulSoup, element
from money import Money

BANRURAL_ERRORS = {
    "INVALID_CREDENTIALS": " Nombre de usuario o credenciales de autentificación inválidas",
    "CHANGE_PASSWORD": "CAMBIO DE CLAVE REQUERIDO, 90 DIAS DESDE LA ULTIMA MODIFICACION",
    "USER_LOCKED": "USUARIO BLOQUEADO TEMPORALMENTE",
    "NO_MOVEMENTS_FOR_DATE": "NO EXISTEN MOVIMIENTOS PARA ESTA CUENTA EN LAS FECHAS REQUERIDAS",
}

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)


class BanruralBaseBank(BaseBank):
    def __init__(self):
        super().__init__(
            login_url="https://www.banrural.com.gt/corp/a/principal.asp",
            accounts_url="https://www.banrural.com.gt/corp/a/consulta_saldos.asp",
            movements_url="https://www.banrural.com.gt/corp/a/estados_cuenta_texto_resp.asp",
            logout_url="https://www.banrural.com.gt/corp/a/default.asp",
        )


class BanruralCorporateBaseBank(BaseBank):
    def __init__(self):
        super().__init__(
            login_url="https://bvnegocios.banrural.com.gt/corp/pages/jsp-ns/login-corp.jsp",
            accounts_url="https://bvnegocios.banrural.com.gt/corp/pages/common/AccountHistoryLookupBoxAction.action",
            movements_url="https://bvnegocios.banrural.com.gt/corp/pages/jsp/account/GetTransactionsAction.action",
            logout_url="https://bvnegocios.banrural.com.gt/corp/web/js/i18n/LoginJavaScript.properties",
        )


class BanruralCorporateBank(Bank):
    def __init__(self, credentials):
        super().__init__("Banrural", BanruralCorporateBaseBank(), credentials)
        self.login_1_url = "https://bvnegocios.banrural.com.gt/corp/pages/jsp-ns/submitUserNameAndCustID.action"
        self.login_2_url = "https://bvnegocios.banrural.com.gt/corp/pages/jsp-ns/loginUserRedirect.action"
        self.accounts_get_url = " https://bvnegocios.banrural.com.gt/corp/pages/jsp/account/accountbalance_index.jsp"
        self.base_host = "https://bvnegocios.banrural.com.gt"
    
    def _get_csrf(self, url):
        response = self._fetch(url)
        fetch_bs = BeautifulSoup(response, features="html.parser")
        csrf = fetch_bs.find("input", {"name": "CSRF_TOKEN"})
        return csrf["value"]

    def login(self):
        login_csrf = self._get_csrf(self.login_url)
        login1_response = self._fetch(
            self.login_1_url,
            {
                "CSRF_TOKEN": login_csrf,
                "CustomerID": "uselessCustID",
                "UserName": self.credentials.username,
                "struts.enableJSONValidation": True,
                "struts.validateOnly": True,
            },
        )

        login2_response = self._fetch(
            self.login_2_url,
            {
                "CSRF_TOKEN": login_csrf,
                "Password": self.credentials.password,
                "CSRF_TOKEN": login_csrf,
            },
        )
    
    def _get_url_for_getting_accounts_url(self):
        get_account_url = self._fetch(self.accounts_get_url)
        get_account_url_bs = BeautifulSoup(get_account_url, features="html.parser")
        scripts = get_account_url_bs.find_all("script")
        for script in scripts:
            if script.string and 'consolidatedbalance_monetario_grid' in script.string:
                variable_parts = script.string.split("=")
                for idx, part in enumerate(variable_parts):
                    if 'consolidatedbalance_monetario_grid' in part:
                        url = part + '=' + variable_parts[idx+1]
                        url = url.split("\"")[1]
                        url = self.base_host + url #+ "&_=" + str(round(time.time() * 1000)) + "&_search=false&nd=1648912961219&rows=10&page=1&sidx=&sord=asc" 
                        return url
    def _get_url_for_accounts(self, fetch_accounts_url):
        account_info = self._fetch(fetch_accounts_url)
        account_info_bs = BeautifulSoup(account_info, features="html.parser")
        scripts = account_info_bs.find_all('script')
        for script in scripts:
            if (script.string and 'options_consolidatedBalanceMonetarioSummaryID.url =' in script.string):
                variable_part = script.string.split("options_consolidatedBalanceMonetarioSummaryID.url =")
                url = variable_part[1].split(";")[0].replace("\"", "") +  "&_=" + str(round(time.time() * 1000)) + "&_search=false&nd=1648912961219&rows=10&page=1&sidx=&sord=asc" 
                url = url.strip()
                url = self.base_host + url
                return url
        
    def fetch_accounts(self):
       
        fetch_accounts_url = self._get_url_for_getting_accounts_url()
        url_accounts = self._get_url_for_accounts(fetch_accounts_url)
        results = self._fetch(url_accounts, json=True)
        accounts = []
        for account in results['gridModel']:

            account = BanruralBankCorporateAccount(
                self, account['ID'], account['nickName'], account['type'], account['currencyCode'],  account['routingNum']
            )
            accounts.append(account)
        return accounts
        
    def get_account(self, number):
        accounts = self.fetch_accounts()
        for account in accounts:
            if account.account_number == number:
                return account

        return None

    def logout(self):
        _ = self._fetch(
            self.logout_url,
        )
        logger.info("Did logout")

        return True


class BanruralBank(Bank):
    def __init__(self, credentials):
        super().__init__("Banrural", BanruralBaseBank(), credentials)

    def login(self):
        login_response = self._fetch(
            self.login_url,
            {
                "UserName": self.credentials.username,
                "password": self.credentials.password,
            },
        )
        login_bs = BeautifulSoup(login_response, features="html.parser")
        error_fields = [
            login_bs.find("td", {"class": "txt_normal"}),
            login_bs.find("td", {"class": "txt_normal_bold"}),
            login_bs.find("script"),
        ]
        error_fields = error_fields[error_fields is not None]
        if error_fields:
            for field in error_fields:
                logger.error("TXT Field %s", field.string)
                if field and BANRURAL_ERRORS["INVALID_CREDENTIALS"] in field.string:
                    logger.error("Invalid Credentials: %s", field.string)
                    raise InvalidCredentialsException(field.string)
                elif field and BANRURAL_ERRORS["CHANGE_PASSWORD"] in field.string:
                    logger.error("Change of password required")
                    raise ChangePasswordRequired(field.string)
                elif field and BANRURAL_ERRORS["USER_LOCKED"] in field.string:
                    raise InvalidCredentialsException(field.string)
        logger.info("Log in finished succesfully")
        return True

    def fetch_accounts(self):
        accounts = []
        logger.info("Will start to fetch accounts")
        response = self._fetch(self.accounts_url)
        accounts_bs = BeautifulSoup(response, features="html.parser")
        account_table = accounts_bs.findAll("tr", {"class": "tabledata_gray"})
        for account_row in account_table:
            text_of_account = account_row.findAll("span")
            alias = text_of_account[0].string.strip()
            account_num = text_of_account[1].string.strip()
            account_type = text_of_account[2].string.strip()
            currency = text_of_account[3].string.strip()
            movements_link = account_row.findAll("a")[1]
            internal_reference = None
            if movements_link:
                link = movements_link["href"]
                internal_reference = self._build_internal_reference_account(link)

            account = BanruralBankAccount(
                self, account_num, alias, account_type, currency, internal_reference
            )
            logger.info("Found new account with number %s", account_num)
            accounts.append(account)
        logger.info("Finish fetching accounts")

        return accounts

    def get_account(self, number):
        accounts = self.fetch_accounts()
        for account in accounts:
            if account.account_number == number:
                return account

        return None

    def logout(self):
        _ = self._fetch(
            self.logout_url,
            headers={"Referer": "https://www.banrural.com.gt/corp/a/menu_nuevo.asp"},
        )
        logger.info("Did logout")

        return True

    def _build_internal_reference_account(self, url):
        query_params = parse_qs(url.split("?")[1], keep_blank_values=True)
        return "{0}|{1}|{2}|{3}".format(
            query_params["alias"][0],
            query_params["cta"][0],
            query_params["moneda"][0],
            query_params["descmoneda"][0],
        )


class BanruralBankCorporateAccount(AbstractBankAccount):
    def _make_query_for_date(self, start_date, end_date, token, url, cookies):
        url_initial = 'https://bvnegocios.banrural.com.gt/corp/pages/jsp/account/index.jsp'
        body_initial = {
            'CSRF_TOKEN': token,
            'TransactionSearch': 'true'
        }
        result = self.bank._fetch(url_initial, body_initial)
        thx = result.split('THX1139=')[1].split(";")[0].replace("'", "")
        print("THX" + thx)
        home_session_cleanup_url = 'https://bvnegocios.banrural.com.gt/corp/pages/jsp/inc/homeSessionCleanup.jsp'
        body = {
            'CSRF_TOKEN': token
        }
        result = self.bank._fetch(home_session_cleanup_url, body)

        body = {
    
    'CSRF_TOKEN': token,
    'TSView': 'true',
    'ResetTSZBADisplay': 'true',
    'operationFlag': '',
    'exportHistoryUrlValue': '/corp/pages/jsp/account/inc/account-history-export-common.jsp?CSRF_TOKEN=8449846631668390886',
    'accountGroup': '1',
    'corporateAccount': '{0},1000,{1},1,false'.format(self.account_number, self.account_bank_reference),
    'StartDateSessionValue': '07/03/2022',
    'EndDateSessionValue': '05/04/2022',
    'GetPagedTransactions.StartDate': '',
    'GetPagedTransactions.EndDate': '',
    'GetPagedTransactions.DateRangeValue': 'Last Week',
    'ammountStart': '',
    'ammountEnd': '',
    'searchDescription': '',
    'searchFlag': 'true',
    'struts.enableJSONValidation': 'true',
    'struts.validateOnly': 'true',


        }
        query = urlencode(body)
        print(query)
        result = self.bank._session.post(url, data=query, headers={
              'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': '*/*',

        }, cookies=cookies).text
        
        body_simple = {
        
                'CSRF_TOKEN': token,
                'TSView': 'true',
                'ResetTSZBADisplay': 'true',
                'operationFlag': '',
                'exportHistoryUrlValue': '/corp/pages/jsp/account/inc/account-history-export-common.jsp?CSRF_TOKEN={0}'.format(token),
                'accountGroup': '1',
                'corporateAccount':  '{0},1000,{1},1,false'.format(self.account_number, self.account_bank_reference),
                'StartDateSessionValue': '07/03/2022',
                'EndDateSessionValue': '05/04/2022',
                'GetPagedTransactions.StartDate':  '07/03/2022',
                'GetPagedTransactions.EndDate':'05/04/2022',
                'GetPagedTransactions.DateRangeValue': '',
                'ammountStart': '',
                'ammountEnd': '',
                'searchDescription': '',
                'searchFlag': 'true',
        }
        query_simple = urlencode(body_simple)

        result = self.bank._session.post(url, data=query_simple, headers={
              'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': '*/*',

        }, cookies=cookies).text
        
        url_account_history = "https://bvnegocios.banrural.com.gt/corp/pages/jsp/account/accounthistory_grid.jsp?THX1139={0}&_={1}".format(thx, str(round(time.time() * 1000)))
        
        result = self.bank._fetch(url_account_history)
    def fetch_movements(self, start_date, end_date):
        self.main_url = "https://bvnegocios.banrural.com.gt/corp/pages/jsp/home/home-page.action"
        self.search_results = 'https://bvnegocios.banrural.com.gt/corp/pages/jsp/account/getSearchResults.action'
        
        response = self.bank._session.get(self.main_url)
        results = response.text
        results_bs = BeautifulSoup(results, features="html.parser")
        print(self.bank._session.cookies.get_dict())
        for script in results_bs.find_all('script'):
            if (script.string and 'CSRF_TOKEN' in script.string):
                token = script.string.split('CSRF_TOKEN')[1].split('\'')[1]
                print(token)
        self._make_query_for_date(start_date, end_date, token, self.search_results, cookies=response.cookies)
        query_dict = {
            'accountIndex': '1',
            'setAccountID': self.account_number,
            'collectionName': 'Transactions',
            'GridURLs': 'GRID_accountHistory',
            '_': str(round(time.time() * 1000)),
            '_search': 'false',
            'nd': str(round(time.time() * 1000)),
            'rows': '50',
            'page': '1',
            'sidx': 'date',
            'sord': 'asc',
        }
        query = urlencode(query_dict)
        full_url = self.bank.movements_url + "?" + query
        results = self.bank._fetch(full_url, json=True)
        movements = []
        for mov in results["gridModel"]:
            if mov['map']['auxCreditDebitNoteMin'] == 'debita':
                ammount = mov['map']['auxCreditDebitValue'] * -1
            else:
                ammount = mov['map']['auxCreditDebitValue']
            ammount = Money(amount=ammount, currency="GTQ")
            description = mov["description"] 
            date = datetime.datetime.strptime(mov["date"], "%d/%m/%Y")
            reference_number = None
            if "referenceNumber" in mov:
                reference_number = mov['referenceNumber']
            movement = Movement(self, mov["ID"], date, description, ammount, reference_number)
            movements.append(movement)
        return movements
        

class BanruralBankAccount(AbstractBankAccount):
    _FILE_NAME = "".join(random.choices(string.digits, k=8))
    PAGINATION_SIZE = 90
    _DEFAULT_HEADERS = {
        "Referer": "https://www.banrural.com.gt/corp/a/consulta_movimientos.asp"
    }

    def _convert_date_to_txt_format(self, date):
        return date.strftime("%d/%m/%Y")

    def _get_initial_dict(self, start_date, end_date):
        date_query_start = self._convert_date_to_txt_format(start_date)
        date_query_end = self._convert_date_to_txt_format(end_date)
        form_data = {
            "ddmCuentas": self.account_bank_reference,
            "txtfechainicial": date_query_start,
            "txtfechafinal": date_query_end,
            "bntTransmitir": "TRANSMITIR",
            "modovista": "TEXTO",
        }
        logger.info("Will request MOVEMENTS with this initial data %s", form_data)
        return form_data

    def _iterate_all_pages(self, start_date, end_date, form_data=None):
        if form_data is None:
            form_data = self._get_initial_dict(start_date, end_date)
        headers = type(self)._DEFAULT_HEADERS
        movements_bs = BeautifulSoup(
            self.bank._fetch(self.bank.movements_url, form_data, headers),
            features="html.parser",
        )
        movements = []
        error = movements_bs.find("div", {"class": "instructions"})
        if error and BANRURAL_ERRORS["NO_MOVEMENTS_FOR_DATE"] in error.text:
            return []
        tables = movements_bs.findAll("table", {"width": "80%"})
        if len(tables) < 3:
            return []
        table = movements_bs.findAll("table", {"width": "80%"})[2]
        if not table:
            return []
        rows = table.findAll(True, {"class": ["tabledata_gray", "tabledata_white"]})
        for row in rows:
            columns = row.findAll("td")
            date = datetime.datetime.strptime(columns[0].text, "%d/%m/%Y")
            description = columns[2].text
            id_doc = columns[3].text
            id_doc_2 = columns[4].text
            ammount = (
                float(columns[5].text.replace(",", ""))
                if columns[5].text != "0.00"
                else float(columns[6].text.replace(",", "")) * -1
            )
            money = Money(amount=ammount, currency="GTQ")
            mov = Movement(self, id_doc, date, description, money, id_doc_2)
            movements.append(mov)
        return movements

    def _get_date_ranges_to_search(self, start_date, end_date):
        timedelta = end_date - start_date
        days_timedelta = timedelta.days
        number_of_iterations = math.ceil(days_timedelta / type(self).PAGINATION_SIZE)
        calculated_start_date = start_date
        date_ranges = []
        for _ in range(0, number_of_iterations):
            calculated_end_range = calculated_start_date + datetime.timedelta(
                days=type(self).PAGINATION_SIZE
            )
            if calculated_end_range > end_date:
                calculated_end_range = end_date
            date_ranges.append((calculated_start_date, calculated_end_range))
            calculated_start_date = calculated_end_range + datetime.timedelta(days=1)
        return date_ranges

    def fetch_movements(self, start_date, end_date):
        dates_to_search = self._get_date_ranges_to_search(start_date, end_date)
        movments = list(
            map(lambda date: self._iterate_all_pages(date[0], date[1]), dates_to_search)
        )
        flatten = reduce(operator.concat, movments, [])
        return flatten
