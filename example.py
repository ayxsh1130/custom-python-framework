from main import SlowAPI, render_template

app = SlowAPI(middlewares=[lambda req: None])

@app.get('/')
def home(request, response):
    response.json({'framework': 'SlowAPI', 'status': 'ok'})

@app.get('/users/{user_id}')
def get_user(request, response, user_id):
    response.json({'user_id': user_id, 'query': request.queries})

@app.post('/echo')
def echo(request, response):
    response.json(request.json(), 201)

@app.route('/items/{item_id}')
class ItemController:
    def get(self, request, response, item_id):
        response.json({'id': item_id})
    def delete(self, request, response, item_id):
        response.json({'deleted': item_id})

if __name__ == '__main__':
    app.run()
