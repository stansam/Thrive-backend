"""
Payment Service
Handles payment processing with Stripe integration
"""

import logging
from typing import Dict, Optional
import stripe
from decimal import Decimal

logger = logging.getLogger(__name__)


class PaymentServiceError(Exception):
    """Base exception for payment service errors"""
    pass


class PaymentService:
    """Service for handling payment operations"""
    
    def __init__(self, config):
        """
        Initialize payment service with configuration
        
        Args:
            config: Flask app config object
        """
        self.stripe_secret_key = config.get('STRIPE_SECRET_KEY')
        self.stripe_publishable_key = config.get('STRIPE_PUBLISHABLE_KEY')
        self.webhook_secret = config.get('STRIPE_WEBHOOK_SECRET')
        
        if self.stripe_secret_key:
            stripe.api_key = self.stripe_secret_key
        else:
            logger.warning("Stripe secret key not configured")
    
    def create_payment_intent(
        self,
        amount: float,
        currency: str = 'usd',
        customer_email: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Create a Stripe payment intent
        
        Args:
            amount: Amount to charge in currency units
            currency: Three-letter currency code (lowercase)
            customer_email: Customer email for receipt
            metadata: Additional metadata to attach
            
        Returns:
            Dict with payment intent details including client_secret
            
        Raises:
            PaymentServiceError: If payment intent creation fails
        """
        try:
            # Convert to cents for Stripe
            amount_cents = int(Decimal(str(amount)) * 100)
            
            intent_params = {
                'amount': amount_cents,
                'currency': currency.lower(),
                'automatic_payment_methods': {'enabled': True},
            }
            
            if customer_email:
                intent_params['receipt_email'] = customer_email
            
            if metadata:
                intent_params['metadata'] = metadata
            
            intent = stripe.PaymentIntent.create(**intent_params)
            
            logger.info(f"Created payment intent: {intent.id}")
            
            return {
                'success': True,
                'paymentIntentId': intent.id,
                'clientSecret': intent.client_secret,
                'amount': amount,
                'currency': currency,
                'status': intent.status
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating payment intent: {str(e)}")
            raise PaymentServiceError(f"Failed to create payment intent: {str(e)}")
        except Exception as e:
            logger.exception("Unexpected error creating payment intent")
            raise PaymentServiceError(f"Unexpected error: {str(e)}")
    
    def confirm_payment(
        self,
        payment_intent_id: str,
        amount: float,
        currency: str
    ) -> Dict:
        """
        Confirm a payment intent
        
        Args:
            payment_intent_id: Stripe payment intent ID
            amount: Expected amount
            currency: Expected currency
            
        Returns:
            Dict with payment confirmation details
            
        Raises:
            PaymentServiceError: If confirmation fails
        """
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            # Verify amount and currency
            expected_amount = int(Decimal(str(amount)) * 100)
            if intent.amount != expected_amount:
                raise PaymentServiceError(
                    f"Amount mismatch: expected {expected_amount}, got {intent.amount}"
                )
            
            if intent.currency != currency.lower():
                raise PaymentServiceError(
                    f"Currency mismatch: expected {currency}, got {intent.currency}"
                )
            
            # Check status
            if intent.status == 'succeeded':
                logger.info(f"Payment confirmed: {payment_intent_id}")
                
                return {
                    'success': True,
                    'status': 'succeeded',
                    'paymentIntentId': intent.id,
                    'transactionId': intent.charges.data[0].id if intent.charges.data else None,
                    'amount': float(intent.amount) / 100,
                    'currency': intent.currency.upper()
                }
            elif intent.status in ['processing', 'requires_action']:
                return {
                    'success': False,
                    'status': intent.status,
                    'message': 'Payment is still processing'
                }
            else:
                return {
                    'success': False,
                    'status': intent.status,
                    'error': 'Payment failed',
                    'message': intent.last_payment_error.message if intent.last_payment_error else 'Unknown error'
                }
                
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error confirming payment: {str(e)}")
            raise PaymentServiceError(f"Failed to confirm payment: {str(e)}")
        except Exception as e:
            logger.exception("Unexpected error confirming payment")
            raise PaymentServiceError(f"Unexpected error: {str(e)}")
    
    def process_refund(
        self,
        payment_intent_id: str,
        amount: Optional[float] = None,
        reason: Optional[str] = None
    ) -> Dict:
        """
        Process a refund for a payment
        
        Args:
            payment_intent_id: Stripe payment intent ID
            amount: Amount to refund (None for full refund)
            reason: Reason for refund
            
        Returns:
            Dict with refund details
            
        Raises:
            PaymentServiceError: If refund fails
        """
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            if not intent.charges.data:
                raise PaymentServiceError("No charges found for this payment intent")
            
            charge_id = intent.charges.data[0].id
            
            refund_params = {'charge': charge_id}
            
            if amount is not None:
                refund_params['amount'] = int(Decimal(str(amount)) * 100)
            
            if reason:
                refund_params['reason'] = 'requested_by_customer'
                refund_params['metadata'] = {'reason_details': reason}
            
            refund = stripe.Refund.create(**refund_params)
            
            logger.info(f"Processed refund: {refund.id} for payment {payment_intent_id}")
            
            return {
                'success': True,
                'status': 'succeeded',
                'refundId': refund.id,
                'amount': float(refund.amount) / 100,
                'currency': refund.currency.upper()
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error processing refund: {str(e)}")
            raise PaymentServiceError(f"Failed to process refund: {str(e)}")
        except Exception as e:
            logger.exception("Unexpected error processing refund")
            raise PaymentServiceError(f"Unexpected error: {str(e)}")
    
    def get_payment_status(self, payment_intent_id: str) -> Dict:
        """
        Get the current status of a payment
        
        Args:
            payment_intent_id: Stripe payment intent ID
            
        Returns:
            Dict with payment status
        """
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            return {
                'success': True,
                'paymentIntentId': intent.id,
                'status': intent.status,
                'amount': float(intent.amount) / 100,
                'currency': intent.currency.upper(),
                'created': intent.created
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error getting payment status: {str(e)}")
            raise PaymentServiceError(f"Failed to get payment status: {str(e)}")
    
    def handle_webhook(self, payload: bytes, signature: str) -> Dict:
        """
        Handle Stripe webhook events
        
        Args:
            payload: Raw request body
            signature: Stripe signature header
            
        Returns:
            Dict with event details
            
        Raises:
            PaymentServiceError: If webhook validation fails
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
            
            logger.info(f"Received webhook event: {event.type}")
            
            # Handle different event types
            if event.type == 'payment_intent.succeeded':
                payment_intent = event.data.object
                return {
                    'event_type': 'payment_succeeded',
                    'payment_intent_id': payment_intent.id,
                    'amount': float(payment_intent.amount) / 100,
                    'currency': payment_intent.currency.upper()
                }
            
            elif event.type == 'payment_intent.payment_failed':
                payment_intent = event.data.object
                return {
                    'event_type': 'payment_failed',
                    'payment_intent_id': payment_intent.id,
                    'error': payment_intent.last_payment_error.message if payment_intent.last_payment_error else None
                }
            
            elif event.type == 'charge.refunded':
                charge = event.data.object
                return {
                    'event_type': 'refund_processed',
                    'charge_id': charge.id,
                    'amount_refunded': float(charge.amount_refunded) / 100,
                    'currency': charge.currency.upper()
                }
            
            return {
                'event_type': event.type,
                'handled': False
            }
            
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Webhook signature verification failed: {str(e)}")
            raise PaymentServiceError("Invalid webhook signature")
        except Exception as e:
            logger.exception("Error handling webhook")
            raise PaymentServiceError(f"Webhook handling error: {str(e)}")
    
    def create_customer(
        self,
        email: str,
        name: Optional[str] = None,
        phone: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Create a Stripe customer
        
        Args:
            email: Customer email
            name: Customer name
            phone: Customer phone
            metadata: Additional metadata
            
        Returns:
            Dict with customer details
        """
        try:
            customer_params = {'email': email}
            
            if name:
                customer_params['name'] = name
            if phone:
                customer_params['phone'] = phone
            if metadata:
                customer_params['metadata'] = metadata
            
            customer = stripe.Customer.create(**customer_params)
            
            logger.info(f"Created Stripe customer: {customer.id}")
            
            return {
                'success': True,
                'customerId': customer.id,
                'email': customer.email
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating customer: {str(e)}")
            raise PaymentServiceError(f"Failed to create customer: {str(e)}")
    
    def calculate_service_fee(self, base_amount: float, percentage: float = 5.0) -> float:
        """
        Calculate service fee
        
        Args:
            base_amount: Base booking amount
            percentage: Service fee percentage (default 5%)
            
        Returns:
            Service fee amount
        """
        return float(Decimal(str(base_amount)) * Decimal(str(percentage)) / Decimal('100'))