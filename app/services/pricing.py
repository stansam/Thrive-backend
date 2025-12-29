from decimal import Decimal

class PricingCalculator:
    """Calculate booking prices and fees"""
    
    # Service fee structure
    DOMESTIC_FEE = Decimal('25.00')
    DOMESTIC_MAX = Decimal('50.00')
    INTERNATIONAL_FEE = Decimal('50.00')
    INTERNATIONAL_MAX = Decimal('100.00')
    URGENT_FEE = Decimal('25.00')
    GROUP_FEE_PER_PERSON = Decimal('15.00')
    GROUP_MIN_SIZE = 5
    
    HOTEL_BOOKING_FEE = Decimal('20.00')
    CAR_RENTAL_FEE = Decimal('15.00')
    ITINERARY_FEE_MIN = Decimal('50.00')
    ITINERARY_FEE_MAX = Decimal('150.00')
    
    @staticmethod
    def calculate_flight_service_fee(
        is_domestic: bool,
        num_passengers: int,
        is_urgent: bool = False,
        is_group: bool = False
    ) -> Decimal:
        """Calculate service fee for flight booking"""
        
        if is_group and num_passengers >= PricingCalculator.GROUP_MIN_SIZE:
            base_fee = PricingCalculator.GROUP_FEE_PER_PERSON * num_passengers
        else:
            if is_domestic:
                base_fee = PricingCalculator.DOMESTIC_FEE
                max_fee = PricingCalculator.DOMESTIC_MAX
            else:
                base_fee = PricingCalculator.INTERNATIONAL_FEE
                max_fee = PricingCalculator.INTERNATIONAL_MAX
            
            # Scale with passengers but cap at max
            base_fee = min(base_fee * num_passengers, max_fee)
        
        # Add urgent fee if applicable
        if is_urgent:
            base_fee += PricingCalculator.URGENT_FEE
        
        return base_fee
    
    @staticmethod
    def calculate_subscription_discount(
        base_fee: Decimal,
        subscription_tier: str
    ) -> Decimal:
        """Calculate discount based on subscription tier"""
        discounts = {
            'bronze': Decimal('0.10'),  # 10% discount
            'silver': Decimal('0.15'),  # 15% discount
            'gold': Decimal('0.20')     # 20% discount
        }
        
        discount_rate = discounts.get(subscription_tier.lower(), Decimal('0'))
        return base_fee * discount_rate
    
    @staticmethod
    def calculate_total_booking_price(
        base_price: Decimal,
        service_fee: Decimal,
        taxes: Decimal = Decimal('0'),
        discount: Decimal = Decimal('0')
    ) -> Decimal:
        """Calculate total booking price"""
        return base_price + service_fee + taxes - discount
    
    @staticmethod
    def apply_referral_credit(
        total_price: Decimal,
        credit_amount: Decimal
    ) -> Tuple[Decimal, Decimal]:
        """Apply referral credit and return (new_total, credit_used)"""
        credit_used = min(credit_amount, total_price)
        new_total = total_price - credit_used
        return new_total, credit_used