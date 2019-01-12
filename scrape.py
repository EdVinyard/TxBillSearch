'''

scrape.py "https://capitol.texas.gov/Search/BillSearchResults.aspx?..."

    Given a TX Legislature Bill Search Results URI, print out the bill numbers
    in the first page of results.

'''
import requests
from bs4 import BeautifulSoup
import sys

if len(sys.argv) != 2:
    print(__doc__)
    exit(1)

response = requests.get(sys.argv[1])
soup = BeautifulSoup(response.text, 'html.parser')

# Extract the bill name from HTML fragments like this:
#
# <table width="95%">
#     <tr width="100%">
#         <td nowrap width="15%">
#             <a href="#" id='86R-HB 26' onClick="SetBillID(this.id); return dropdownmenu(this, event, menu)" onMouseout="delayhidemenu()">
#                 <img src="../Images/txicon.gif" class="noPrint" alt="Click for options"/>
#             </a> 
#             <a href=../BillLookup/History.aspx?LegSess=86R&Bill=HB26 target="_new">
#                 HB 26   
#             </a>
#         </td>
# ...
#
# Start by finding the constant txicon.gif image tag, then navigate to the 
# bill name.

for icon in soup.find_all(name='img', attrs={'src':'../Images/txicon.gif'}):
    td = icon.parent.parent
    bill_link = td.contents[3]
    print(bill_link.string.strip())
