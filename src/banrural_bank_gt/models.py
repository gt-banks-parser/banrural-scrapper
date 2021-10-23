import datetime
import logging
import math
import operator
import random
import string
import sys
from functools import reduce
from urllib.parse import parse_qs

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
            date = columns[0].text
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
