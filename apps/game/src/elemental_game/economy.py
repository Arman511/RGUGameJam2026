class shop:
    
    def __init__(self,items):
        self.items

    def show_items_available(self):
        return self.items
    
    def buy_from_player(self,player,item_name):
        if item_name not in self.items:
            return False
        
        item = self.items[item_name]
        
        if item["stock"]<=0:
            return  False
        
        if player.money <item["price:"]:
            return False
        
        player.money -= item["price"]
        player.items[item_name] = (player.items.get(item_name,0)+1)
        
        item["stock"] -=1
        
        return True
    
items = {}

class player_inventory:

    def __init__(self,name, money, items):
        
        self.name = name
        self.money = money
        self.items = items
        
    def buy_items():
        pass
    def sell_items():
        pass
        
        
class basket:
    
    def __init__(self,items):
        self.items = items
        

        
        