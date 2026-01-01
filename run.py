from app import create_app
from tabulate import tabulate

app = create_app()

def print_routes():
    table = []
    for rule in app.url_map.iter_rules():
        methods = ",".join(sorted(rule.methods))
        url = url_for(rule.endpoint, **{arg: f"<{arg}>" for arg in rule.arguments})
        table.append([rule.endpoint, url, methods])
    app.logger.info(tabulate(table, headers=["Endpoint", "URL", "Methods"]))

if __name__ == '__main__':
    print_routes()
    app.run(debug=True, port=5000)
