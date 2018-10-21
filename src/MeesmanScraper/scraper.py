from MeesmanScraper import config as cfg
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
import pandas as pd
import dateparser
import time
from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database


class WebScraper:

    def __init__(self, verbose):
        self.verbose = verbose
        conf = cfg.get_configuration()
        self.user_meesman = conf['Meesman'].get('user')
        self.pw_meesman = conf['Meesman'].get('password')
        self.host_mysql = conf['MySQL'].get('host')
        self.user_mysql = conf['MySQL'].get('user')
        self.pw_mysql = conf['MySQL'].get('password')
        self.db_mysql = conf['MySQL'].get('database')
        self.engine = create_engine('mysql://{}:{}@{}/{}'.format(self.user_mysql, self.pw_mysql,
                                                                 self.host_mysql, self.db_mysql))
        if not database_exists(self.engine.url):
            create_database(self.engine.url)

    def etl_transactie_table(self):
        # Extract
        if self.verbose:
            print("Extract transactie data")
        browser = webdriver.Chrome()
        browser.get('https://mijn.meesman.nl/login')
        username = browser.find_element_by_id('username')
        username.send_keys(self.user_meesman)
        time.sleep(1)
        password = browser.find_element_by_id('password')
        password.send_keys(self.pw_meesman)
        time.sleep(1)
        login = browser.find_element_by_xpath('//*[@id="login-submit"]')
        login.click()
        transacties = browser.find_element_by_link_text('Transacties')
        transacties.click()

        table = browser.find_element_by_class_name('meesmantable')
        table_html = table.get_attribute('outerHTML')
        df = pd.read_html(table_html, thousands='.', decimal=',')
        meesmantable = df[0]
        check = self.check_exists_by_link_text(browser, 'Volgende pagina')
        while check:
            next_page = browser.find_element_by_link_text('Volgende pagina')
            next_page.click()
            table = browser.find_element_by_class_name('meesmantable')
            table_html = table.get_attribute('outerHTML')
            df = pd.read_html(table_html, thousands='.', decimal=',')
            meesmantable = meesmantable.append(df[0])
            check = self.check_exists_by_link_text(browser, 'Volgende pagina')
        browser.close()

        # Transform
        if self.verbose:
            print("Transform transactie data")
        meesmantable['Datum'] = meesmantable.Datum.map(lambda x: dateparser.parse(x, languages=['nl']))
        meesmantable['Bedrag'] = meesmantable.Bedrag.str.replace('[€\s.]', '').str.replace(',', '.').astype(float)
        meesmantable = meesmantable.sort_values(['Fonds', 'Datum'])
        meesmantable.loc[meesmantable.Transactie == 'Aankoop', 'Transactie'] = 'Periodieke Aankoop'
        meesmantable['Betaling'] = meesmantable.apply(lambda x: self.is_buy(x), axis=1)
        meesmantable['Aantal'] = meesmantable.apply(lambda x: self.is_sale(x), axis=1)
        meesmantable['Totaal_Aantal'] = meesmantable.groupby('Fonds').Aantal.cumsum()
        meesmantable['Totaal_Betaling'] = meesmantable.groupby('Fonds').Betaling.cumsum()
        meesmantable['Totaal_Waarde'] = meesmantable['Koers'] * meesmantable['Totaal_Aantal']
        meesmantable = meesmantable.drop('Afschrift', axis=1)
        meesmantable['Key'] = (meesmantable.Datum.dt.strftime('%d%m%y') +
                               meesmantable.Fonds.apply(lambda x: ''.join(word[0] for word in x.split())))

        # Load
        if self.verbose:
            print("Load transactie data")
        con = self.engine.connect()
        meesmantable.to_sql('transacties', con=con, if_exists='replace', index=False)
        con.close()

        if self.verbose:
            print('ETL job for transactie table is done!')

    def etl_portefeuille_table(self):
        # Extract
        if self.verbose:
            print("Extract portefeuille data")
        browser = webdriver.Chrome()
        browser.get('https://mijn.meesman.nl/login')
        username = browser.find_element_by_id('username')
        username.send_keys(self.user_meesman)
        time.sleep(1)
        password = browser.find_element_by_id('password')
        password.send_keys(self.pw_meesman)
        time.sleep(1)
        login = browser.find_element_by_xpath('//*[@id="login-submit"]')
        login.click()
        portefeuille = browser.find_element_by_link_text('Portefeuille')
        portefeuille.click()
        table = browser.find_element_by_class_name('meesmantable')
        table_html = table.get_attribute('outerHTML')
        df = pd.read_html(table_html, thousands='.', decimal=',')
        meesmantable = df[0].dropna()
        browser.close()

        # Transform
        if self.verbose:
            print("Transform portefeuille data")
        meesmantable = meesmantable.assign(
            Datum=meesmantable.Datum.map(lambda x: dateparser.parse(x, languages=['nl'])))
        meesmantable['Koers'] = meesmantable.Koers.str.replace('[€\s.]', '').str.replace(',', '.').astype(float)
        meesmantable['Waarde'] = meesmantable.Waarde.str.replace('[€\s.]', '').str.replace(',', '.').astype(float)
        meesmantable['Actuele weging'] = meesmantable['Actuele weging'].str.replace('\%', '').astype(int) / 100

        # Load
        if self.verbose:
            print("Load portefeuille data")
        con = self.engine.connect()
        meesmantable.to_sql('portefeuille', con=con, if_exists='append', index=False)
        con.close()

        if self.verbose:
            print('ETL job for portefeuille table is done!')

    @staticmethod
    def check_exists_by_link_text(browser, link_text):
        try:
            browser.find_element_by_link_text(link_text)
        except NoSuchElementException:
            return False
        return True

    @staticmethod
    def is_buy(row):
        if row['Transactie'] != 'Dividend Herbelegging':
            return row['Bedrag']
        return 0

    @staticmethod
    def is_sale(row):
        if row['Bedrag'] < 0:
            return -row['Aantal']
        return row['Aantal']