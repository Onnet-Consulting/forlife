version: '3'
services:
  database:
    build: ./dockerfiles/postgres/${POSTGRES_VERSION}/alpine
    ports:
      - ${DB_PORT}:5432
    volumes:
      - ./pg_data:/var/lib/postgresql/data/pg_data
    restart: always
    networks:
      - default
    environment:
      - POSTGRES_DB=postgres
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - PGDATA=/var/lib/postgresql/data/pg_data
  web:
    build: ./dockerfiles/odoo/${ODOO_VERSION}
    volumes:
      - ./requirements.txt:/opt/requirements.txt
      - ./odoo.conf:/etc/odoo/odoo.conf
      - ./addons:/mnt/extra-addons
      - ./odoo_storage:/var/lib/odoo
    command: /bin/bash -c "pip3 install -r /opt/requirements.txt && odoo"
    links:
      - "database:database"
    environment:
      - HOST=database
      - USER=${DB_USER}
      - PASSWORD=${DB_PASSWORD}
    restart: always
    ports:
      - "${WEB_PORT}:8069"
      - "${WEB_LONG_POLLING_PORT}:8072"
    depends_on:
      - "database"
    networks:
      - default
networks:
  default:
    driver: bridge
    driver_opts:
      com.docker.network.driver.mtu: 1450
