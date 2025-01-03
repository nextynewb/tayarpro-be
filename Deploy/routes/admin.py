from fastapi import APIRouter, Depends, Path, HTTPException
from models import Service, User, Tyre, Orders, OrdersDetail, Notification
from database import sessionLocal
from typing_extensions import Annotated
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from routes.account import get_current_user, Token
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import extract, func
import time
import uuid
import random


def get_db():
    db = sessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


router = APIRouter()


class ServiceRequest(BaseModel):
    service_id: str = Field(min_length=3, max_length=50)
    typeid: str = Field(min_length=3, max_length=50)
    description: str = Field(min_length=3, max_length=50)
    cartype: str = Field(min_length=3, max_length=50)
    price: float = Field(gt=0)
    status: str = Field(min_length=3, max_length=50)


@router.post('/add_service', tags=["Admin Action"])
async def add_service(db: db_dependency, user: user_dependency, service: ServiceRequest):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    check_admin = db.query(User).filter(
        User.accountid == user['accountid'],
        User.isadmin == 'Y'
    ).first()

    if not check_admin:
        raise HTTPException(status_code=401, detail="You are not admin")

    check_service = db.query(Service).filter(
        Service.serviceid == service.service_id).first()

    if check_service:
        raise HTTPException(
            status_code=400, detail="Service ID already exists")

    new_service = Service(
        serviceid=service.service_id,
        typeid=service.typeid,
        description=service.description,
        cartype=service.cartype,
        price=service.price,
        status=service.status,
        createdby=user['accountid'],
        createdat=datetime.now()
    )

    db.add(new_service)
    db.commit()


class NewTyreRequests(BaseModel):
    itemid: Optional[str] = Field(min_length=3, max_length=50, default=None)
    itemid: str = Field(min_length=3, max_length=50)
    brandid:  str = Field(min_length=3, max_length=50)
    description: str = Field(min_length=3, max_length=50)
    cartype: str = Field(min_length=3, max_length=50)
    image_link: str = Field(min_length=3, max_length=200)
    price: float = Field(gt=0)
    tyresize: str = Field(min_length=3, max_length=50)
    speedindex: str = Field(min_length=1, max_length=50)
    loadindex: int = Field(gt=0)
    stockunit: int = Field(gt=0)
    status: str = Field(min_length=3, max_length=50)


@router.post('/add_tyre', tags=["Admin Action"])
async def admin_add_products(db: db_dependency, user: user_dependency, tyre: NewTyreRequests):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    check_admin = db.query(User).filter(
        User.accountid == user['accountid']).first()

    if not check_admin:
        raise HTTPException(status_code=401, detail="You are not admin")

    check_tyre = db.query(Tyre).filter(
        Tyre.itemid == tyre.itemid).first()

    if check_tyre:
        raise HTTPException(status_code=400, detail="Tyre ID already exists")

    details = ["Safest Tyre", "Best Tyre", "Most Durable Tyre"]

    new_tyre = Tyre(
        itemid=tyre.itemid,
        productid="TYRE",
        brandid=tyre.brandid,
        description=tyre.description,
        cartype=tyre.cartype,
        image_link=tyre.image_link,
        unitprice=float(tyre.price),
        details=details,
        tyresize=tyre.tyresize,
        speedindex=tyre.speedindex,
        loadindex=int(tyre.loadindex),
        stockunit=int(tyre.stockunit),
        status=tyre.status,
        createdat=datetime.now(),
        createdby=user['accountid']
    )

    db.add(new_tyre)
    db.commit()

    return {
        "message": "Tyre added successfully",
        "tyre": new_tyre
    }


@router.put('/update_tyre', tags=["Admin Action"])
async def update_tyres(db: db_dependency, user: user_dependency, update_tyre: NewTyreRequests):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    check_admin = db.query(User).filter(
        User.accountid == user['accountid']).first()

    if not check_admin:
        raise HTTPException(status_code=401, detail="You are not admin")

    tyre = db.query(Tyre).filter(
        Tyre.itemid == update_tyre.itemid).first()

    if not tyre:
        raise HTTPException(status_code=404, detail="Tyre not found")

    tyre.brandid = update_tyre.brandid
    tyre.description = update_tyre.description
    tyre.cartype = update_tyre.cartype
    tyre.image_link = update_tyre.image_link
    tyre.unitprice = update_tyre.price
    tyre.tyresize = update_tyre.tyresize
    tyre.speedindex = update_tyre.speedindex
    tyre.loadindex = update_tyre.loadindex
    tyre.stockunit = update_tyre.stockunit
    tyre.status = update_tyre.status
    db.commit()

    return tyre


@router.post('/all_users', tags=["Admin Action"])
async def all_users(db: db_dependency, user: user_dependency):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    check_admin = db.query(User).filter(
        User.accountid == user['accountid'],
        User.isAdmin == 'Y'
    ).first()

    if not check_admin:
        raise HTTPException(status_code=401, detail="You are not admin")

    all_users = db.query(User).order_by(User.isAdmin.desc()).all()

    return all_users


@router.post('/give_admin_rights', tags=["Admin Action"])
async def give_admin_rights(db: db_dependency, user: user_dependency, accountid: str):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    check_admin = db.query(User).filter(
        User.accountid == user['accountid']).first()

    if not check_admin:
        raise HTTPException(status_code=401, detail="You are not admin")

    user = db.query(User).filter(
        User.accountid == accountid).first()

    user.isAdmin = 'Y'

    db.commit()
    db.refresh(user)

    return {
        "message": "Admin rights given",
        "user": user
    }


@router.post('/remove_admin_rights', tags=["Admin Action"])
async def remove_admin_rights(db: db_dependency, user: user_dependency, accountid: str):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    check_admin = db.query(User).filter(
        User.accountid == user['accountid']).first()

    if not check_admin:
        raise HTTPException(status_code=401, detail="You are not admin")

    user = db.query(User).filter(
        User.accountid == accountid).first()

    user.isAdmin = 'N'

    db.commit()
    db.refresh(user)

    return {
        "message": "Admin rights removed",
        "user": user
    }


@router.put('/edit_service', tags=["Admin Action"])
async def edit_service(db: db_dependency, user: user_dependency, service_update: ServiceRequest):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    check_admin = db.query(User).filter(
        User.accountid == user['accountid']).first()

    if not check_admin:
        raise HTTPException(status_code=401, detail="You are not admin")

    service = db.query(Service).filter(
        Service.serviceid == service_update.service_id).first()

    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    service.typeid = service_update.typeid
    service.description = service_update.description
    service.cartype = service_update.cartype
    service.price = service_update.price
    service.status = service_update.status

    db.commit()
    db.refresh(service)


@router.post('/brand_distributions', tags=["Admin Action"])
async def brand_distributions(db: db_dependency, user: user_dependency):
    order_items = db.query(OrdersDetail).filter(
        OrdersDetail.productid.like('T%')).all()
    for order in order_items:
        order.brandid = db.query(Tyre).filter(
            Tyre.itemid == order.productid).first().brandid
    print(order_items)

    return {
        "message": "Success"
    }


@router.post('/get_sales_and_orders_data', tags=["Admin Action"])
async def get_sales_and_orders_data(db: db_dependency, user: user_dependency):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    month_now = datetime.now().month
    year_now = datetime.now().year

    months = []
    sales = []
    orders = []

    # Get sales for the past six months
    sales_data = {}
    for i in range(7):
        month = (month_now - i) % 12 or 12
        year = year_now if month_now - i > 0 else year_now - 1
        month_name = datetime(year, month, 1).strftime('%B')
        monthly_sales = db.query(func.sum(Orders.totalprice)).filter(
            extract('month', Orders.createdat) == month,
            extract('year', Orders.createdat) == year
        ).scalar()
        sales_data[month_name] = monthly_sales or 0
        sales.append(monthly_sales or 0)
        months.append(month_name)

    num_orders_data = {}

    for i in range(7):
        month = (month_now - i) % 12 or 12
        year = year_now if month_now - i > 0 else year_now - 1
        month_name = datetime(year, month, 1).strftime('%B')
        monthly_orders = db.query(func.count(Orders.orderid)).filter(
            extract('month', Orders.createdat) == month,
            extract('year', Orders.createdat) == year
        ).scalar()
        num_orders_data[month_name] = monthly_orders or 0
        orders.append(monthly_orders or 0)

    sales.reverse()
    orders.reverse()
    months.reverse()

    return {
        "six_months_sales": sales_data,
        "six_months_orders": num_orders_data,
        "sales": sales,
        "orders": orders,
        "months": months
    }


@router.post('/get_registered_users', tags=["Admin Action"])
async def get_registered_users(db: db_dependency, user: user_dependency):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    month_now = datetime.now().month
    year_now = datetime.now().year

    user_data = {}
    months = []
    registred_users = []

    for i in range(7):
        month = (month_now - i) % 12 or 12
        year = year_now if month_now - i > 0 else year_now - 1
        month_name = datetime(year, month, 1).strftime('%B')
        monthly_users = db.query(func.count(User.accountid)).filter(
            extract('month', User.createdat) == month,
            extract('year', User.createdat) == year
        ).scalar()
        user_data[month_name] = monthly_users or 0
        registred_users.append(monthly_users or 0)
        months.append(month_name)

    registred_users.reverse()
    months.reverse()

    return {
        "six_months_users": user_data,
        "months": months,
        "registered_users": registred_users
    }


@router.post('/get_order_statistics', tags=["Admin Action"])
async def get_orders_by_month(db: db_dependency, user: user_dependency):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    month_now = datetime.now().month
    year_now = datetime.now().year

    months = []
    orders = []

    for i in range(7):
        month = (month_now - i) % 12 or 12
        year = year_now if month_now - i > 0 else year_now - 1
        month_name = datetime(year, month, 1).strftime('%B')
        monthly_orders = db.query(func.count(Orders.orderid)).filter(
            extract('month', Orders.createdat) == month,
            extract('year', Orders.createdat) == year
        ).scalar()
        orders.append(monthly_orders or 0)
        months.append(month_name)

    orders.reverse()
    months.reverse()

    return {
        "months": months,
        "orders": orders
    }


@router.post('/data_dashboard', tags=["Admin Action"])
async def data_dashboard(db: db_dependency, user: user_dependency):

    month_now = datetime.now().month
    year_now = datetime.now().year
    previous_month = month_now - 1

    total_revenue = db.query(func.sum(Orders.totalprice)).filter(
        extract('month', Orders.createdat) == month_now,
        extract('year', Orders.createdat) == year_now
    ).scalar()

    num_orders = db.query(func.count(Orders.orderid)).filter(
        extract('month', Orders.createdat) == month_now,
        extract('year', Orders.createdat) == year_now
    ).scalar()

    this_month_user = db.query(func.count(User.accountid)).filter(
        extract('month', User.createdat) == month_now,
        extract('year', User.createdat) == year_now
    ).scalar()

    if month_now == 1:
        previous_month = 12

        previous_total_revenue = db.query(func.sum(Orders.totalprice)).filter(
            extract('month', Orders.createdat) == previous_month,
            extract('year', Orders.createdat) == year_now - 1
        ).scalar()

        previous_month_users = db.query(func.count(User.accountid)).filter(
            extract('month', User.createdat) == previous_month,
            extract('year', User.createdat) == year_now - 1
        ).scalar()
    else:

        previous_total_revenue = db.query(func.sum(Orders.totalprice)).filter(
            extract('month', Orders.createdat) == previous_month,
            extract('year', Orders.createdat) == year_now
        ).scalar()

        previous_month_users = db.query(func.count(User.accountid)).filter(
            extract('month', User.createdat) == previous_month,
            extract('year', User.createdat) == year_now
        ).scalar()

    return {
        "month_now": month_now,
        "previous_month": previous_month,
        "total_revenue": total_revenue,
        "previous_total_revenue": previous_total_revenue,
        "num_orders": num_orders,
        "this_month_user": this_month_user,
        "previous_month_users": previous_month_users
    }


@router.post('/get_notifications', tags=["Admin Action"])
async def get_notifications(db: db_dependency, user: user_dependency):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    notifications = db.query(Notification).order_by(
        Notification.createdat.desc()).limit(10).all()

    return notifications


"""
TODO:

1. Add Products (Tyre)
2. Update Service
3. Update Products
4. View All Users
5. Give Admin Rights
6. Dashboard Data
7. View All Transactions
"""


@router.get('/hit_notifications', tags=["Admin Action"])
async def hit_notifications(db: db_dependency):

    notifications = [
        {
            "message": "Received new order from lol@gmail.com!",
            "status": "active",
            "category": "Order",
            "icon": "fa fa-shopping-cart",
        },
        {
            "message": "Uh oh! Tyre T002 stock is running low!",
            "status": "active",
            "category": "Stock",
            "icon": "fa fa-exclamation-triangle",
        },
        {
            "message": "aniq@gmail.com has just registered!",
            "status": "active",
            "category": "User",
            "icon": "fa fa-user-plus",
        },
        {
            "message": "New order placed by vincent.23@example.com!",
            "status": "active",
            "category": "Order",
            "icon": "fa fa-shopping-cart",
        },
        {
            "message": "Stock for Tyre T008 is below threshold!",
            "status": "active",
            "category": "Stock",
            "icon": "fa fa-exclamation-triangle",
        },
        {
            "message": "vincent.1@example.com has just registered!",
            "status": "active",
            "category": "User",
            "icon": "fa fa-user-plus",
        },
        {
            "message": "Received new order from 33@example.org!",
            "status": "active",
            "category": "Order",
            "icon": "fa fa-shopping-cart",
        },
        {
            "message": "Stock for Tyre T008 is running low!",
            "status": "active",
            "category": "Stock",
            "icon": "fa fa-exclamation-triangle",
        },
        {
            "message": "christopher3220@example.org has just registered!",
            "status": "active",
            "category": "User",
            "icon": "fa fa-user-plus",
        },
        {
            "message": "New order placed by aniqfaidi@example.com!",
            "status": "active",
            "category": "Order",
            "icon": "fa fa-shopping-cart",
        }
    ]

    for notification in notifications:
        new_notification = Notification(
            notificationid=str(uuid.uuid4()),
            message=notification["message"],
            status=notification["status"],
            category=notification["category"],
            icon=notification["icon"],
            createdat=datetime.now()
        )
        db.add(new_notification)
        db.commit()
        time.sleep(1)

    notifications = db.query(Notification).all()

    return notifications


@router.post('/random_notifications', tags=["Admin Action"])
async def random_notifications(db: db_dependency):
    emails = ["rahmanrom@gmail.com", "inbaraj@gmail.com", "amerasyraf@gmail.com", "natekumar@gmail.com",
              "jonathan@gmail.com", "Arifaiman@gmail.com", "Mariahanwar@gmail.com", "ruben@gmail.com", "yeepeng@gmail.com", "aniqfaidi@gmail.com", "aliyabat@gmail.com"]
    categories = ["Order", "Stock", "User"]
    icons = ["fa fa-shopping-cart",
             "fa fa-exclamation-triangle", "fa fa-user-plus"]
    products = [
        "T001", "T003", "T005", "T009", "T008", "T007", "T002", "T004", "T006"
    ]

    random_category = random.choice(categories)

    if random_category == "Order":
        random_emails = random.choice(emails)
        random_float = random.uniform(50, 500)
        random_float = round(random_float, 2)
        message = f"Received new order from {random_emails}! and the total order price is MYR {random_float}"
    elif random_category == "Stock":
        random_products = random.choice(products)
        message = f"Stock for Tyre {random_products} is running low!"
    else:
        random_emails = random.choice(emails)
        message = f"{random_emails} has just registered!"

    random_icon = random.choice(icons)

    new_notification = Notification(
        notificationid=str(uuid.uuid4()),
        message=message,
        status="active",
        category=random_category,
        icon=random_icon,
        createdat=datetime.now()
    )

    db.add(new_notification)
    db.commit()
