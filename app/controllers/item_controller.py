from app.models.item import Item

items_db = [{'id': 1, 'name': 'user1', 'description': '測試使用者1號', 'price': 1234}]


def get_items():
	return items_db


def get_item(item_id: int):
	for item in items_db:
		if item.id == item_id:
			return item
	return None


def create_item(item: Item):
	items_db.append(item)
	return item
