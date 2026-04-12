# src/domain/models/finance.py

from src.domain import models



class ExchangeRate(models.Model):
    date = models.DateField(unique=True, db_index=True)
    buy_price = models.DecimalField(max_digits=10, decimal_places=3)
    sell_price = models.DecimalField(max_digits=10, decimal_places=3)
    origin = models.CharField(max_length=50, default='apimigo')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.date}: B:{self.buy_price} - S:{self.sell_price}"