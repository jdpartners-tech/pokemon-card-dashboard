import os
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from backend.models import Card, PriceSnapshot
from backend.database import Base

DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_engine(DATABASE_URL)

sample_cards = [
    {"name": "Charizard", "set_name": "Base Set", "card_number": "4/102",
     "snkrdunk_id": "charizard-base-4", "pricecharting_id": "charizard-base-set",
     "snkrdunk_price_hkd": 85000, "pricecharting_price_usd": 10800},
    {"name": "Blastoise", "set_name": "Base Set", "card_number": "2/102",
     "snkrdunk_id": "blastoise-base-2", "pricecharting_id": "blastoise-base-set",
     "snkrdunk_price_hkd": 32000, "pricecharting_price_usd": 4100},
    {"name": "Venusaur", "set_name": "Base Set", "card_number": "15/102",
     "snkrdunk_id": "venusaur-base-15", "pricecharting_id": "venusaur-base-set",
     "snkrdunk_price_hkd": 18000, "pricecharting_price_usd": 2300},
    {"name": "Pikachu", "set_name": "Base Set", "card_number": "58/102",
     "snkrdunk_id": "pikachu-base-58", "pricecharting_id": "pikachu-base-set",
     "snkrdunk_price_hkd": 9500, "pricecharting_price_usd": 1200},
    {"name": "Mewtwo", "set_name": "Base Set", "card_number": "10/102",
     "snkrdunk_id": "mewtwo-base-10", "pricecharting_id": "mewtwo-base-set",
     "snkrdunk_price_hkd": 14000, "pricecharting_price_usd": 1800},
    {"name": "Lugia", "set_name": "Neo Genesis", "card_number": "9/111",
     "snkrdunk_id": "lugia-neo-9", "pricecharting_id": "lugia-neo-genesis",
     "snkrdunk_price_hkd": 42000, "pricecharting_price_usd": 5400},
    {"name": "Ho-Oh", "set_name": "Neo Revelation", "card_number": "7/64",
     "snkrdunk_id": "hooh-neo-7", "pricecharting_id": "hooh-neo-revelation",
     "snkrdunk_price_hkd": 28000, "pricecharting_price_usd": 3600},
    {"name": "Umbreon", "set_name": "Neo Discovery", "card_number": "13/75",
     "snkrdunk_id": "umbreon-neo-13", "pricecharting_id": "umbreon-neo-discovery",
     "snkrdunk_price_hkd": 22000, "pricecharting_price_usd": 2800},
]

USD_TO_HKD = 7.8

with Session(engine) as session:
    session.query(PriceSnapshot).delete()
    session.query(Card).delete()
    session.flush()

    for data in sample_cards:
        card = Card(
            name=data["name"],
            set_name=data["set_name"],
            card_number=data["card_number"],
            snkrdunk_id=data["snkrdunk_id"],
            pricecharting_id=data["pricecharting_id"],
        )
        session.add(card)
        session.flush()

        snapshot = PriceSnapshot(
            card_id=card.id,
            snkrdunk_price_hkd=data["snkrdunk_price_hkd"],
            pricecharting_price_usd=data["pricecharting_price_usd"],
            pricecharting_price_hkd=round(data["pricecharting_price_usd"] * USD_TO_HKD, 2),
            usd_to_hkd_rate=USD_TO_HKD,
        )
        session.add(snapshot)

    session.commit()
    print(f"Inserted {len(sample_cards)} cards with price snapshots into Neon DB.")
