from flask import Flask, request
from flask_restful import Resource, Api
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from sqlalchemy.dialects.postgresql import MONEY
from argparse import ArgumentParser

arg_parser = ArgumentParser()
arg_parser.add_argument('--db-name', default='canal_service', help='Database name')
arg_parser.add_argument('--db-user', default='canal_service', help='Database user')
arg_parser.add_argument('--db-pass', default='canal_service', help='Database user password')    
arg_parser.add_argument('--db-host', default='localhost', help='Database host')
arg_parser.add_argument('--db-port', default='5432', help='Database name')
args = arg_parser.parse_args()

app = Flask(__name__)

db_url = 'postgresql+psycopg2://{}:{}@{}:{}/{}'.format(
    args.db_user, args.db_pass, args.db_host, args.db_port, args.db_name)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
api = Api(app)
db = SQLAlchemy()
db.init_app(app)
ma = Marshmallow(app)

class Purchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    update_datetime = db.Column(db.DateTime)
    cost_usd = db.Column(MONEY)
    cost_rub = db.Column(MONEY)
    delivery_date = db.Column(db.Date)

class PurchaseSchema(ma.Schema):
    class Meta:
        fields = ('id', 'update_datetime', 'cost_usd', 'cost_rub', 'delivery_date')
        model = Purchase

purchase_schema = PurchaseSchema()
purchases_schema = PurchaseSchema(many=True)

class PurchaseAPI(Resource):
    def get(self, id):
        purchase = Purchase.query.filter(Purchase.id == id).first_or_404()
        return purchase_schema.dump(purchase)

class PurchasesAPI(Resource):
    def get(self):
        query = Purchase.query
        if 'limit' in request.args:
            query = query.limit(request.args['limit'])
        if 'offset' in request.args:
            query = query.offset(request.args['offset'])
        purchases = query.all()
        return purchases_schema.dump(purchases)

api.add_resource(PurchasesAPI, '/purchases/')
api.add_resource(PurchaseAPI, '/purchase/<int:id>')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
