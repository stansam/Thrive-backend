import pytest
from unittest.mock import patch, MagicMock
from app.services.payment import PaymentService, PaymentServiceError

@pytest.fixture
def payment_service(app):
    with app.app_context():
        # Config provided by app fixture via TestConfig
        return PaymentService(app.config)

def test_create_payment_intent(payment_service):
    with patch('app.services.payment.stripe.PaymentIntent.create') as mock_create:
        mock_create.return_value = MagicMock(
            id="pi_123",
            client_secret="secret_123",
            status="requires_payment_method"
        )
        
        result = payment_service.create_payment_intent(100.00, "USD")
        
        assert result['success'] is True
        assert result['paymentIntentId'] == "pi_123"
        assert result['clientSecret'] == "secret_123"
        
        # Verify call args (amount should be in cents)
        mock_create.assert_called_once()
        _, kwargs = mock_create.call_args
        assert kwargs['amount'] == 10000
        assert kwargs['currency'] == 'usd'

def test_create_payment_intent_error(payment_service):
    # Need to import stripe exception or mock it
    import stripe
    with patch('app.services.payment.stripe.PaymentIntent.create') as mock_create:
        mock_create.side_effect = stripe.error.StripeError("Mock Stripe Error")
        
        with pytest.raises(PaymentServiceError):
            payment_service.create_payment_intent(100.00, "USD")

def test_confirm_payment_success(payment_service):
    with patch('app.services.payment.stripe.PaymentIntent.retrieve') as mock_retrieve:
        mock_intent = MagicMock()
        mock_intent.id = "pi_123"
        mock_intent.amount = 10000
        mock_intent.currency = "usd"
        mock_intent.status = "succeeded"
        mock_intent.charges.data = [MagicMock(id="ch_123")]
        
        mock_retrieve.return_value = mock_intent
        
        result = payment_service.confirm_payment("pi_123", 100.00, "USD")
        
        assert result['success'] is True
        assert result['status'] == "succeeded"
        assert result['transactionId'] == "ch_123"

def test_confirm_payment_mismatch(payment_service):
    with patch('app.services.payment.stripe.PaymentIntent.retrieve') as mock_retrieve:
        mock_intent = MagicMock()
        mock_intent.amount = 5000 # 50.00
        mock_intent.currency = "usd"
        mock_retrieve.return_value = mock_intent
        
        with pytest.raises(PaymentServiceError) as excinfo:
            payment_service.confirm_payment("pi_123", 100.00, "USD")
        
        assert "Amount mismatch" in str(excinfo.value)
