from weapons_plotly import make_weapon_graph
from all_recipe_items import make_item_graph
import sqlite3
import dash
from dash import dcc
from dash import html

output_dir = "./output"
weapon_names = {
    "great-sword",
    "long-sword",
    "sword-and-shield",
    "dual-blades",
    "hammer",
    "hunting-horn",
    "lance",
    "gunlance",
    "switch-axe",
    "charge-blade",
    "insect-glaive",
    "light-bowgun",
    "heavy-bowgun",
    "bow",
}

def main():
    item_ids = {"115"}
    conn = sqlite3.connect("../mhw.db")  
    for item in item_ids:
        print(f"* Item: {item}")
        make_item_graph(item, conn, output_dir)
    # for weapon in weapon_names:
    #     print(f"* Weapon: {weapon}")
    #     make_weapon_graph(weapon, conn, output_dir)
    fig = make_weapon_graph("great-sword", conn, output_dir)
    app = dash.Dash()
    app.layout = html.Div([dcc.Graph(figure=fig)])

    app.run_server(debug=True, use_reloader=False)
    
    conn.close()

if __name__ == "__main__":
    main()
