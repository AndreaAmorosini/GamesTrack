import rawgpy

rawg = rawgpy.RAWG("User-Agent, this should identify your app")
results = rawg.search("Warframe")  # defaults to returning the top 5 results
game = results[0]
game.populate()  # get additional info for the game

print(game.name)

print(game.description)

for store in game.stores:
    print(store.url)

rawg.login("someemail@example.com", "somepassword")

me = rawg.current_user()

print(me.name)  # print my name, equivalent to print(self.username)

me.populate()  # gets additional info for the user

for game in me.playing:
    print(game.name)  # prints all the games i'm currently playing
