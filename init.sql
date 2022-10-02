CREATE TABLE purchase
(
    id INTEGER,
    update_datetime TIMESTAMP DEFAULT NOW(),
    cost_usd MONEY,
    cost_rub MONEY,
    delivery_date DATE,
    PRIMARY KEY (id, update_datetime)
);

COMMENT ON TABLE purchase IS 'Закупка';
COMMENT ON COLUMN purchase.id IS 'Номер заказа';
COMMENT ON COLUMN purchase.update_datetime IS 'Время, когда были получены данные из таблицы';
COMMENT ON COLUMN purchase.cost_usd IS 'Стоимость в долларах';
COMMENT ON COLUMN purchase.cost_rub IS 'Стоимость в рублях';
COMMENT ON COLUMN purchase.delivery_date IS 'Срок поставки';

CREATE TABLE overdue_purchase
(
    purchase_id INTEGER PRIMARY KEY
);

COMMENT ON TABLE overdue_purchase IS 'Закупка, у которой истек срок поставки';
COMMENT ON COLUMN overdue_purchase.purchase_id IS 'ID закупки';
