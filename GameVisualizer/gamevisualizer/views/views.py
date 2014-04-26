from pyramid.view import view_config


@view_config(route_name='home', renderer='gamevisualizer:templates/mytemplate.pt')
def my_view(request):
    return {'project': 'GameVisualizer'}
