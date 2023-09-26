import sqlite3
import urllib.request, urllib.parse, urllib.error
import json
from tkinter import *
from PIL import ImageTk,Image
import shutil
import os

conn = sqlite3.connect('pokedex.sqlite')
cur = conn.cursor()
cur.execute('CREATE TABLE IF NOT EXISTS Pokemon(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, hp INTEGER, attack INTEGER, defense INTEGER, specialattack INTEGER, specialdefense INTEGER, speed INTEGER)')
cur.execute('CREATE TABLE IF NOT EXISTS Type(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)')
cur.execute('CREATE TABLE IF NOT EXISTS Connect(pokemon_id INTEGER, type_id INTEGER, PRIMARY KEY (pokemon_id, type_id))')
stat_dict = {'hp':'hp', 'attack':'attack', 'defense':'defense', 'special-attack':'specialattack', 'special-defense':'specialdefense', 'speed':'speed'}
stat_options = ['hp', 'attack', 'defense', 'special-attack', 'special-defense', 'speed']

pokemon_url = 'https://pokeapi.co/api/v2/pokemon/'

class pokemon_view(Frame):
    def __init__(self, master, button_text):
        super().__init__(master)
        
        self.name_label = Label(self)
        self.name_label.grid(row=0, column=0)
        self.pokemon_image = Label(self, height=100, width=100)
        self.pokemon_image.grid(row=1, column=0)
        self.save = Button(self, text=button_text)
        self.save.grid(row=2, column=0)
        self.stat_labels = list()
        for index in range(6):
            stat_label = Label(self, width=20)
            stat_label.grid(row=3+index%2, column=index%3)
            self.stat_labels.append(stat_label)
        self.type_label = Label(self)
        self.type_label.grid(row=1, column=1)
        
    
def search_pokemon(pokemon_name):
    if len(pokemon_name) > 0:
        pokemon_name = pokemon_name.lower().replace(' ', '-')
        url = pokemon_url + pokemon_name
        request = urllib.request.Request(url)
        request.add_header('User-Agent', 'Mozilla/5.0 (X11; U; Linux i686) Gecko/20071127 Firefox/2.0.0.11')
        try:
            unparsed_data = urllib.request.urlopen(request)
            if unparsed_data.status == 200:
                #Load Data
                data = json.load(unparsed_data)
                picture = urllib.request.urlopen(data['sprites']['other']['official-artwork']['front_default']).read()
                fhand = open('pokemonimage.png', 'wb')
                fhand.write(picture)
                fhand.close()
                import_image = ImageTk.PhotoImage(Image.open('pokemonimage.png').resize((100, 100), Image.LANCZOS))
                
                #Update save_frame
                save_frame.pokemon_image.configure(image=import_image)
                save_frame.pokemon_image.image=import_image
                save_frame.save.configure(command=lambda: save_pokemon(data))
                for index, stat in enumerate(data['stats']):
                    save_frame.stat_labels[index].configure(text=stat['stat']['name'] + ': ' + str(stat['base_stat']))
                types = ''
                for item in data['types']:
                    types = types + item['type']['name'] + ', '
                types = types[:-2]
                save_frame.type_label.configure(text='Type: ' + types)
                
                #Hide/Show correct frame
                save_frame.grid(row=1, column=0, rowspan=4)
                error_frame.grid_forget()
        except urllib.error.HTTPError:
            error_frame.grid(row=1, column=0)
            save_frame.grid_forget()
    else:
        error_frame.grid(row=1, column=0)
        save_frame.grid_forget()

def save_pokemon(data):
    cur.execute('SELECT * FROM Pokemon WHERE name=(?)', (data['name'],))
    if cur.fetchone() is None:
        #Insert Pokemon Name
        cur.execute('INSERT OR IGNORE INTO Pokemon(name) VALUES (?)', (data['name'],))
        cur.execute('SELECT id FROM Pokemon WHERE name=(?)', (data['name'],))
        name_id = cur.fetchone()[0]

        #Insert Pokemon Stats
        cur.execute('UPDATE Pokemon SET hp=? WHERE name=?', (data['stats'][0]['base_stat'], data['name']))
        for stat in data['stats']:
            cur.execute('UPDATE Pokemon SET %s = ? WHERE name=?' % (stat_dict[stat['stat']['name']],), (stat['base_stat'], data['name']))

        #Insert Pokemon Type
        for item in data['types']:
            cur.execute('INSERT OR IGNORE INTO Type(name) VALUES (?)', (item['type']['name'],))
            cur.execute('SELECT id FROM TYPE WHERE name=(?)', (item['type']['name'],))
            type_id = cur.fetchone()[0]
            cur.execute('INSERT OR IGNORE INTO Connect(pokemon_id, type_id) VALUES(?, ?)', (name_id, type_id))

        #Save Image
        destination = os.getcwd()+'/images'
        if not os.path.exists(destination):
            os.mkdir(destination)
        shutil.copy('pokemonimage.png', destination)
        os.rename(destination+'/pokemonimage.png', destination+'/'+data['name']+'.png')

        conn.commit()

def remove_pokemon(pokemon_name):
    cur.execute('SELECT id FROM Pokemon WHERE name=?', (pokemon_name,))
    pokemon_id = cur.fetchone()[0]
    cur.execute('SELECT type_id FROM Connect WHERE pokemon_id=?', (pokemon_id,))
    type_id = cur.fetchall()
    cur.execute('DELETE FROM Connect WHERE pokemon_id=?', (pokemon_id,))
    cur.execute('DELETE FROM Pokemon WHERE name=?', (pokemon_name,))
    for item in type_id:
        cur.execute('SELECT * From Connect WHERE type_id=?', (item[0],))
        if cur.fetchone() is None:
            cur.execute('DELETE FROM Type WHERE id=?', (item[0],))
    
    conn.commit()
    os.remove(os.getcwd() + '/images/' + pokemon_name + '.png')
    view_saved(user_filter)

def view_saved(filter_type):
    global user_filter
    user_filter = filter_type
    if filter_type is None or filter_type == 'All':
        cur.execute('SELECT Pokemon.name, Pokemon.hp, Pokemon.attack, Pokemon.defense, Pokemon.specialattack, Pokemon.specialdefense, Pokemon.speed, Type.name FROM Pokemon JOIN TYPE JOIN Connect ON Pokemon.id=Connect.pokemon_id AND Type.id=Connect.type_id')
    else:
        cur.execute('SELECT Pokemon.name FROM Pokemon JOIN Type Join Connect ON Pokemon.id=Connect.pokemon_id AND Type.id=Connect.type_id WHERE Type.name=?', (filter_type,))
        parsed_list = [item[0] for item in cur.fetchall()]
        cur.execute('SELECT Pokemon.name, Pokemon.hp, Pokemon.attack, Pokemon.defense, Pokemon.specialattack, Pokemon.specialdefense, Pokemon.speed, Type.name FROM Pokemon JOIN TYPE JOIN Connect ON Pokemon.id=Connect.pokemon_id AND Type.id=Connect.type_id WHERE Pokemon.name in ({seq})'.format(seq=','.join(['?']*len(parsed_list))), (parsed_list))
    saved_pokemons = cur.fetchall()
    
    #Remove previous saved
    for widget in frame.winfo_children():
        widget.destroy()
    
    #Filter by type
    cur.execute('SELECT name from TYPE')
    type_choices = [item[0] for item in cur.fetchall()]
    if len(type_choices) > 0:
        type_choices.insert(0, 'All')
        clicked = StringVar()
        type_menu = OptionMenu(frame, clicked, *type_choices, command=lambda selected=clicked.get(): view_saved(selected))
        type_menu.grid(row=0, column=1, sticky='n')
    
    #Load each saved pokemon
    pokemon_name = None
    custom_frame = None
    for index, pokemon in enumerate(saved_pokemons):
        if pokemon_name != pokemon[0]:
            pokemon_name = pokemon[0]
            custom_frame = pokemon_view(frame, 'Remove Pokemon')
            custom_frame.configure(borderwidth=2, relief='solid')
            custom_frame.name_label.configure(text=pokemon_name.replace('-', ' '))
            import_image = ImageTk.PhotoImage(Image.open(os.getcwd()+'/images/'+pokemon[0]+'.png').resize((100, 100), Image.LANCZOS))
            custom_frame.pokemon_image.configure(image=import_image)
            custom_frame.pokemon_image.image=import_image
            custom_frame.save.configure(command=lambda pokemon_name=pokemon_name: remove_pokemon(pokemon_name))
            for i in range(1, 7):
                custom_frame.stat_labels[i-1].configure(text=stat_options[i-1] + ': ' + str(pokemon[i]))

            custom_frame.type_label.configure(text='Type: ' + pokemon[7])
            custom_frame.grid(row=index, column=0)
        else:
            custom_frame.type_label.configure(text=custom_frame.type_label.cget('text') + ', ' + pokemon[7])
    
    canvas.update_idletasks()
    canvas.config(scrollregion=frame.bbox())
    super_frame.pack(fill='both', expand=True)
    error_frame.grid_forget()
    search_frame.pack_forget()
    
def view_search():
    super_frame.pack_forget()
    save_frame.grid_forget()
    error_frame.grid_forget()
    search_frame.pack(side='top')
    user_filter = None

#Root
root = Tk()
root.title('Pokedex')
root.iconbitmap('pokeball.ico')
root.geometry('620x400')

#Navigation
nav_frame = Frame(root)
search_button = Button(nav_frame, text='Search', command=view_search)
search_button.grid(row=0, column=0)
save_button = Button(nav_frame, text='Saved', command=lambda: view_saved(None))
save_button.grid(row=0, column=1)
nav_frame.pack()

#Search frame
search_frame = Frame(root)
container_frame = Frame(search_frame)
pokemon_entry = Entry(container_frame)
enter_button = Button(container_frame, text='Search Pokemon', fg='red', borderwidth=2, relief="solid", command=lambda: search_pokemon(pokemon_entry.get()))
enter_button.grid(row=0, column=1)
pokemon_entry.grid(row=0, column=0)
container_frame.grid(row=0,column=0)
search_frame.pack()
save_frame = pokemon_view(search_frame, 'Save Pokemon')

#Error frame
error_frame = Frame(search_frame)
error_text = Label(error_frame, text='Unable to find Pokemon', fg='red')
error_text.grid(row=0, column=0)

#Scrollable saved pokemon frame
super_frame = Frame(root)
canvas = Canvas(super_frame)
canvas.pack(side='left', fill='both', expand=True)
my_scrollbar = Scrollbar(super_frame, orient=VERTICAL, command=canvas.yview)
my_scrollbar.pack(side='right', fill='y')
canvas.configure(yscrollcommand=my_scrollbar.set)
canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion = canvas.bbox("all")))
frame = Frame(canvas)
canvas.create_window((0,0), window=frame, anchor='nw')
user_filter = None

root.mainloop()