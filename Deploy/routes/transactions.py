from fastapi import APIRouter, Depends, Path, HTTPException
from models import Cart, Tyre, Service, Orders, OrdersDetail, Appointment, RegisterCar, Notification, User
from database import sessionLocal
from typing_extensions import Annotated
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from routes.account import get_current_user, Token
import uuid
from datetime import datetime, date, time


# Dependency
def get_db():
    db = sessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


router = APIRouter()


"""
Add Service to Cart
"""


class addServiceToCart(BaseModel):
    service_id: str
    quantity: int = Field(..., gt=0,
                          description="Quantity must be greater than 0")


class addTyreToCart(BaseModel):
    tyre_id: str
    quantity: int = Field(..., gt=0,
                          description="Quantity must be greater than 0")


@router.post('/add_service_to_cart', tags=["Cart"])
async def add_service_to_cart(db: db_dependency, user: user_dependency, service: addServiceToCart):
    """
    service_id: int
    quantity: int


    If not user: Unauthorized
    Check Cart:
    If ServiceID exists, increment quantity
    Else, add new service to Cart

    """

    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Find the Service ID in Cart

    check_services = db.query(Service).filter(
        Service.serviceid == service.service_id).first()

    if not check_services:
        raise HTTPException(status_code=404, detail="Service not found")

    check_cart = db.query(Cart).filter(
        Cart.accountid == user['accountid'], Cart.productid == service.service_id).first()

    if check_cart:
        check_cart.quantity += service.quantity
        db.commit()
        return {"message": "Service added to Cart"}

    else:
        new_cart = Cart(
            accountid=user['accountid'],
            productid=service.service_id,
            quantity=service.quantity,
            unitprice=check_services.price,
            description=check_services.description,
            createdat=datetime.now()
        )

        db.add(new_cart)
        db.commit()

        all_carts = db.query(Cart).filter(
            Cart.accountid == user['accountid']).all()
        return {"message": "Service added to Cart", "carts": all_carts}


@router.post('/add_tyre_to_cart', tags=["Cart"])
async def add_tyre_to_cart(db: db_dependency, user: user_dependency, tyre: addTyreToCart):
    """
    tyre_id: int
    quantity: int

    If not user: Unauthorized
    Check Cart:
    If TyreID exists, increment quantity
    Else, add new tyre to Cart
    """

    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Find the Tyre ID in Cart

    check_tyres = db.query(Tyre).filter(
        Tyre.itemid == tyre.tyre_id).first()

    if not check_tyres:
        raise HTTPException(status_code=404, detail="Tyre not found")

    if check_tyres.stockunit < tyre.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")

    check_cart = db.query(Cart).filter(
        Cart.accountid == user['accountid'], Cart.productid == tyre.tyre_id).first()

    if check_cart:
        check_cart.quantity += tyre.quantity
        db.commit()

    else:
        new_cart = Cart(
            accountid=user['accountid'],
            productid=tyre.tyre_id,
            quantity=tyre.quantity,
            unitprice=check_tyres.unitprice,
            description=check_tyres.description,
            createdat=datetime.now()
        )

        db.add(new_cart)
        db.commit()

    if check_cart:
        check_tyres.stockunit -= tyre.quantity
        db.commit()
        return {"message": "Tyre added to Cart"}

    all_carts = db.query(Cart).filter(
        Cart.accountid == user['accountid']).all()

    return {
        "message": "Tyre added to Cart",
        "carts": all_carts
    }


@router.get('/get_cart', tags=['Cart'])
async def cart_using_get(db: db_dependency, user: user_dependency):
    """
    Cart data using get method
    """
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    cart = db.query(Cart).filter(Cart.accountid ==
                                 user['accountid']).order_by(Cart.createdat).all()
    return cart


@router.post('/get_cart', tags=['Cart'])
async def cart_using_post(db: db_dependency, user: user_dependency):
    """
    Cart data using post method
    """
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    cart = db.query(Cart).filter(Cart.accountid == user['accountid']).all()

    return cart


@router.post('/empty_cart', tags=['Cart'])
async def empty_cart(db: db_dependency, user: user_dependency):
    """
    Empty the cart
    """
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    db.query(Cart).filter(Cart.accountid == user['accountid']).delete()
    db.commit()

    return {"message": "Cart emptied"}


"""
=======================
Checkout, Invoicing and Appointments
=======================
"""


class CheckoutCarts(BaseModel):
    """
    Appointment Date: YYYY-MM-DD
    Appointment Time:   HH:MM
    Appointment Bay:   1, 2, 3, 4, 5
    Car ID:
    """
    car_id: int = Field(..., description="Car ID")
    appointment_date: date = Field(default=date(
        2023, 1, 24), description="Appointment Date")
    appointment_time: time = Field(default=time(
        14, 30), description="Appointment Time")
    appointment_bay: int = Field(..., description="Appointment Bay")
    payment_method: str = Field(
        default="Cash", description="Payment Method(Cash, Card, E-Wallet)")


@router.post('/checkout', tags=['Checkout'], summary="Checkout the cart")
async def checkout(db: db_dependency, user: user_dependency, checkout: CheckoutCarts):
    """
    Pre-check:
    1. Check if a user is logged in
    2. Check if the cart is empty

    ----

    1. Create Order
    2. Copy all of the item in carts to OrderDetail
    3. Create Appointment
    4. Link the Appointment ID to Order
    """
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    all_carts = db.query(Cart).filter(
        Cart.accountid == user['accountid']).all()

    if not all_carts:
        raise HTTPException(status_code=400, detail="Cart is empty")

    order_id = str(uuid.uuid4())
    total_price = 0

    check_car_exists = db.query(RegisterCar).filter(
        RegisterCar.carid == checkout.car_id, RegisterCar.accountid == user['accountid']).first()

    if not check_car_exists:
        raise HTTPException(status_code=404, detail="Car not found")

    try:

        for cart in all_carts:
            total_price = total_price + (cart.unitprice * cart.quantity)

        new_order = Orders(
            orderid=order_id,
            accountid=user['accountid'],
            totalprice=total_price,
            createdat=datetime.now(),
            paymentmethod=checkout.payment_method
        )

        db.add(new_order)
        db.commit()

        for cart in all_carts:
            new_order_detail = OrdersDetail(
                orderid=order_id,
                productid=cart.productid,
                quantity=cart.quantity,
                unitprice=cart.unitprice,
                carid=checkout.car_id,
                totalprice=(cart.unitprice * cart.quantity)
            )

            db.add(new_order_detail)
            db.commit()

        # Empty the cart
        db.query(Cart).filter(Cart.accountid == user['accountid']).delete()
        db.commit()

        new_appointment = Appointment(
            appointmentid=str(uuid.uuid4()),
            accountid=user['accountid'],
            appointmentdate=datetime.combine(
                checkout.appointment_date, checkout.appointment_time),
            createdat=datetime.now(),
            status="Future",
            appointment_bay=checkout.appointment_bay,
            carid=checkout.car_id
        )

        db.add(new_appointment)
        db.commit()

        # Update the order with the appointment ID
        db.query(Orders).filter(Orders.orderid == order_id).update(
            {"appointmentid": new_appointment.appointmentid})
        db.commit()

        user_details = db.query(User).filter(
            User.accountid == user['accountid']).first()

        email = user_details.email

        # Create Notification
        new_notification = Notification(
            notificationid=str(uuid.uuid4()),
            message=f"New order placed by {email} with total price of RM {total_price}",
            status="Active",
            icon="fas fa-shopping-cart",
            category="Order",
            createdat=datetime.now()
        )

        db.add(new_notification)
        db.commit()

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "message": "Checkout successful",
        "order_id": order_id,
        "appointment_id": new_appointment.appointmentid
    }


@ router.post('/get_all_orders', tags=['Orders'])
async def get_all_orders(db: db_dependency, user: user_dependency):
    """
    Get all orders
    """
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    all_orders = db.query(Orders).filter(
        Orders.accountid == user['accountid']).all()

    return all_orders


@ router.post('/get_order_detail', tags=['Orders'])
async def get_order_detail(db: db_dependency, user: user_dependency, order_id: str):
    """
    Get order detail by order_id
    """
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    order_detail = db.query(OrdersDetail).filter(
        OrdersDetail.orderid == order_id).all()

    order = db.query(Orders).filter(Orders.orderid == order_id).first()

    if not order_detail:
        raise HTTPException(status_code=404, detail="Order not found")

    return {
        "order": order,
        "order_detail": order_detail
    }


@ router.post('/update_cart_quantity/{product_id}/{new_quantity}', tags=['Cart'])
async def update_cart_quantity(
        product_id: str,
        new_quantity: int,
        db: db_dependency,
        user: user_dependency):
    """
    Update cart item quantity using path parameters

    Parameters:
        - product_id: ID of the product in cart
        - new_quantity: New quantity to set
    """
    try:
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")

        if new_quantity < 1:
            raise HTTPException(
                status_code=400,
                detail="Quantity must be greater than 0"
            )

        cart_item = db.query(Cart).filter(
            Cart.accountid == user['accountid'],
            Cart.productid == product_id
        ).first()

        if not cart_item:
            raise HTTPException(status_code=404, detail="Cart item not found")

        check_tyres = db.query(Tyre).filter(
            Tyre.itemid == product_id).first()

        if cart_item.quantity > new_quantity:
            check_tyres.stockunit += cart_item.quantity - new_quantity
            db.commit()

        elif cart_item.quantity < new_quantity:
            if check_tyres.stockunit < new_quantity - cart_item.quantity:
                raise HTTPException(
                    status_code=400, detail="Insufficient stock")

            check_tyres.stockunit -= new_quantity - cart_item.quantity
            db.commit()

        cart_item.quantity = new_quantity
        db.commit()

        return {
            "message": "Cart quantity updated",
            "product_id": product_id,
            "quantity": new_quantity
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@ router.delete('/delete_cart_item/{product_id}', tags=['Cart'])
async def delete_cart_item(
        product_id: str,
        db: db_dependency,
        user: user_dependency):
    """
    Remove an item from the cart

    Parameters:
        - product_id: ID of the product to remove from cart
    Returns:
    """
    try:
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")

        cart_item = db.query(Cart).filter(
            Cart.accountid == user['accountid'],
            Cart.productid == product_id
        ).first()

        if not cart_item:
            raise HTTPException(status_code=404, detail="Cart item not found")

        db.delete(cart_item)
        db.commit()

        return {"message": "Cart item deleted"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@ router.post('/get_carts_by_details', tags=['Cart'])
async def get_carts_by_details(db: db_dependency, user: user_dependency, accountid: str, productid: str):
    """
    Get all carts by details
    """
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    all_carts = db.query(Cart).filter(
        Cart.accountid == accountid, Cart.productid == productid).all()

    return all_carts
