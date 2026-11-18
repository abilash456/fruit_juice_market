from sqlmodel import SQLModel, Session, create_engine, select
from config import DATABASE_URL
from app.models.models import User, Category, Product
from app.utils.security import hash_password

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)

def get_session():
    with Session(engine) as session:
        yield session

def create_db_and_seed():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        admin = session.exec(select(User).where(User.email == "admin@fruitjuice.local")).first()
        if not admin:
            session.add(User(
                name="Administrator", email="admin@fruitjuice.local",
                password_hash=hash_password("Admin123!"), role="admin"
            ))
        if not session.exec(select(Category)).first():
            names = ["Classic", "Citrus", "Berry", "Seasonal"]
            categories = [Category(name=n) for n in names]
            session.add_all(categories)
            session.commit()
            session.refresh(categories[0])
            cat_map = {c.name: c.id for c in session.exec(select(Category)).all()}
            products = [
                ("Mango Magic", "Sweet mango juice made from ripe mangoes.", 90, 100, "Classic", "🥭"),
                ("Orange Zest", "Fresh and tangy orange juice.", 75, 88, "Citrus", "🍊"),
                ("Berry Bliss", "A refreshing blend of berries.", 120, 135, "Berry", "🍓"),
                ("Watermelon Wave", "Light and refreshing watermelon juice.", 80, 89, "Seasonal", "🍉"),
                ("Pineapple Punch", "Tropical pineapple goodness.", 95, 110, "Seasonal", "🍍"),
                ("Apple Fresh", "Crisp apple juice for any time of day.", 85, 95, "Classic", "🍎"),
                ("Grape Glow", "Rich grape flavour in every sip.", 100, 115, "Classic", "🍇"),
                ("Lemon Lift", "A bright citrus refresher.", 60, 70, "Citrus", "🍋"),
                ("Pomegranate Pop", "Deep, fruity pomegranate juice.", 130, 145, "Berry", "❤️"),
                ("Mixed Fruit", "A colourful mix of favourite fruits.", 110, 125, "Classic", "🍹"),
            ]
            for name, desc, price, old, cat, emoji in products:
                session.add(Product(name=name, description=desc, price=price,
                                    original_price=old, category_id=cat_map[cat],
                                    emoji=emoji, stock=30, is_active=True))
        session.commit()
