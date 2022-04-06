import requests

url = "https://bvnegocios.banrural.com.gt/corp/pages/jsp/account/getSearchResults.action"

payload='CSRF_TOKEN=7449996129673559816&corporateAccount=3885009280-1%2C1000%2C660110110%2C1%2Cfalse&GetPagedTransactions.DateRangeValue=Last%2B5%2BMovements&struts.enableJSONValidation=true&struts.validateOnly=true'
headers = {
  'Accept': '*/*',
  'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
  'Connection': 'keep-alive',
  'Content-Type': 'application/x-www-form-urlencoded',
  'Cookie': 'DefaultTheme=SAP; JSESSIONID=00011CJxlBKlDn_UIB0KqCqFSTf:-302PQA; visid_incap_2637999=jnJBikYrSdmCg8liwFa4Go5JRmIAAAAAQUIPAAAAAADNlRPGuxMna0G/9UPuaZIP; __utmc=206434304; __utmz=206434304.1648849533.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none); dvsst=null; igfvalue=null; __utma=206434304.1741654855.1648849533.1648849533.1648909388.2; dvssv=cc7c3d3d2a01e6a398c77b88661be3a3f4a4409b8f3b4e07680851f6f1c59907; incap_ses_1598_2637999=9u2LLFjge1XcD0KLjzwtFs/MSmIAAAAAW8bjDsjFf2gBpdJTrie0lg==; JSESSIONID=0001lsZhKH2yRhMf0uwNVFJ-eRn:-20H1LT',
  'Origin': 'https://bvnegocios.banrural.com.gt',
  'Referer': 'https://bvnegocios.banrural.com.gt/corp/pages/jsp/home/index.jsp',
  'Sec-Fetch-Dest': 'empty',
  'Sec-Fetch-Mode': 'cors',
  'Sec-Fetch-Site': 'same-origin',
  'Sec-GPC': '1',
  'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.60 Safari/537.36',
  'X-Requested-With': 'XMLHttpRequest'
}

response = requests.request("POST", url, headers=headers, data=payload)

print(response.text)
