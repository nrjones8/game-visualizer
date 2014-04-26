from pyramid.view import view_defaults
from pyramid.view import view_config
from pyramid.response import Response

@view_defaults(route_name='game_espn_id')
class RESTView(object):
    def __init__(self, request):
        self.request = request

    @view_config(request_method='GET')
    def get(self):
        some_dict = {'foo' : 1, 'bar' : 2, 'id' : self.request.matchdict['id']}
        return Response(str(some_dict))