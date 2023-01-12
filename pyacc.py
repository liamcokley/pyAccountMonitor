from flask import Flask, render_template, request, redirect, jsonify
from datetime import datetime
from decimal import Decimal
import piecash
import prettytable
import csv

app = Flask(__name__)

@app.before_first_request
def _init_book():

    print("#### initialising books...")

    book = piecash.create_book("mybook.gnucash", overwrite=True)

    accMain = piecash.Account(name="My Account", type="ASSET", commodity=book.default_currency, parent=book.root_account)
    accOpening = piecash.Account(name="Opening Balance", type="ASSET", commodity=book.default_currency, parent=book.root_account)

    accSpend = piecash.Account(name="Spend", type="ASSET", commodity=book.default_currency, parent=book.root_account)
    book.save()

    book.flush()
    book.close()

@app.route('/')
def transactions_table():

    book = piecash.open_book("mybook.gnucash")

    transactions = book.transactions

    table = prettytable.PrettyTable()

    table.field_names = ["Date", "Description", "FromAcc", "ToAcc", "Amount"]

    for transaction in transactions:
        table.add_row([
            transaction.post_date, transaction.description,
            transaction.splits[0].account.name, transaction.splits[1].account.name,
            transaction.splits[0].value])

    table_html = table.get_html_string()

    book.close()

    return render_template('transactions_table.html', table=table_html)

    app = Flask(__name__)

@app.route('/api/bank_accounts')
def bank_accounts():
    print("### IN /API/BANK_ACCOUNTS ###")

    book = piecash.open_book("mybook.gnucash")

    bank_accounts = book.root_account.children


    data = {
        'name': 'Bank Accounts',
        'children': [{'name': account.name} for account in bank_accounts]
    }


    return jsonify(data)

@app.route('/process_csv', methods=['POST'])
def process_csv():
    # Get the uploaded CSV file
    csv_file = request.files['csv_file']

    csv_rows = []
    for byte_line in csv_file.stream.readlines():
        csv_rows.append(str(byte_line))

    # create a new pretty table
    table = prettytable.PrettyTable()

    # Read the CSV file and process the row
    rows = []
    reader = csv.reader(csv_rows)
    for row in reader:
        table.add_row(row)
        rows.append(row)

    add_transaction_table(table)

    table_html = table.get_html_string() 

    return render_template('upload_results.html', table=table.get_html_string())

def add_transaction_table(table):

    # open our account book
    book = piecash.open_book("mybook.gnucash", readonly=False)

    accMain = book.accounts[0]
    accSpend = book.accounts[2]

    for row in table.rows:
        amount = Decimal(row[1])
        description = row[2]
        date_str = row[0].split("'")[1]
        dateobj = datetime.strptime(date_str, "%d/%m/%Y").date()


        print("### new transaction.")
        print("date: " + date_str)
        print("amount: " + str(amount))
        print("description: " + description)

        
        # Create a new transaction
        transaction = piecash.Transaction(currency=book.default_currency, post_date=dateobj, description=description)

        # Create a split for the transaction
        splitSpend = piecash.Split(account=accSpend, value=amount)
        splitTake = piecash.Split(account=accMain, value=-1*Decimal(amount))

        # Add the split to the transaction
        transaction.splits.append(splitTake)
        transaction.splits.append(splitSpend)

    # Save the changes to the book
    book.save()

    return

@app.route('/create_transaction')
def create_transaction():
    return render_template('create_transaction.html')

@app.route('/upload_transactions')
def upload_transactions():
    return render_template('upload_transactions.html')

@app.route('/show_accounts')
def show_accounts():
    return render_template('show_accounts.html')

@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    # Get the form data
    date_obj = datetime.strptime(request.form['date'], "%Y-%m-%d").date()
    description = request.form['description']
    amount = request.form['amount']

    # open our account book
    book = piecash.open_book("mybook.gnucash", readonly=False)

    accMain = book.accounts[0]
    accSpend = book.accounts[2]

    # Create a new transaction
    transaction = piecash.Transaction(currency=book.default_currency, post_date=date_obj, description=description)

    # Create a split for the transaction
    splitSpend = piecash.Split(account=accSpend, value=amount)
    splitTake = piecash.Split(account=accMain, value=-1*Decimal(amount))

    # Add the split to the transaction
    transaction.splits.append(splitTake)
    transaction.splits.append(splitSpend)

    # Save the changes to the book
    book.save()

    # Redirect the user to the transactions table
    return redirect(location='/')



if __name__ == '__main__':
    app.run()