from backend.models import Card, PortfolioItem


def test_card_has_new_fields():
    c = Card()
    assert hasattr(c, 'image_url')
    assert hasattr(c, 'accent_color')
    assert hasattr(c, 'snkrdunk_url')
    assert hasattr(c, 'pricecharting_url')
    assert hasattr(c, 'psa_population')
    assert hasattr(c, 'sales_per_day')


def test_portfolio_item_model_exists():
    p = PortfolioItem()
    assert hasattr(p, 'card_id')
    assert hasattr(p, 'purchase_price_hkd')
    assert hasattr(p, 'purchased_at')
