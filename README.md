\# Webhook Delivery Platform



A service that reliably delivers events to customers' servers.

It guarantees at-least-once delivery with retries, exponential

backoff with jitter, and a dead-letter state, while keeping

each customer's data isolated.



Creation is protected by an idempotency key the client sends with each event. A unique constraint on customer and key makes the database reject a second insert, even when two requests race, and the API returns the original event. Delivery is at-least-once, so duplicates are possible by design, because a lost response forces a retry. Receivers handle that using the event id, and we guarantee we never lose an event instead of promising we never repeat one.



\## Status

Database schema complete. API and worker in progress.



\## MERMAID

erDiagram

&#x09;direction TB

&#x20;   CUSTOMERS {

&#x20;       uuid id PK ""

&#x20;       text name ""

&#x20;       timestampz created\_at ""

&#x20;   }

&#x09;EVENTS {

&#x09;	uuid id PK ""  

&#x20;       uuid customer\_id FK "" 

&#x20;       text idempotency\_key UK ""

&#x09;	text type  ""  

&#x20;       jsonb payload ""

&#x20;       timestampz created\_at ""

&#x09;}



&#x09;DELIVERIES {

&#x09;	uuid id PK ""  

&#x09;	uuid event\_id FK "" 

&#x20;       uuid endpoint\_id FK "" 

&#x09;	text status  "pending, succeeded, dead"

&#x20;       int retry\_count ""

&#x20;       timestampz next\_attempt\_at  ""



&#x09;}



&#x09;ENDPOINTS {

&#x20;       uuid id PK ""

&#x20;       uuid customer\_id FK ""

&#x20;       text url ""

&#x20;       text signing\_secret ""

&#x20;       boolean is\_active ""

&#x20;       text\[] subscribed\_event\_types ""

&#x09;}

&#x20;   DELIVERY\_ATTEMPTS {

&#x20;       uuid id PK ""

&#x20;       uuid delivery\_id FK ""

&#x20;       int response\_time\_ms ""

&#x20;       text error ""

&#x20;       timestampz attempted\_at ""

&#x20;       int status\_code ""



&#x20;   }





CUSTOMERS ||--o{ EVENTS : owns

CUSTOMERS ||--o{ ENDPOINTS : owns

EVENTS ||--o{ DELIVERIES : triggers

ENDPOINTS ||--o{ DELIVERIES : receives

DELIVERIES ||--o{ DELIVERY\_ATTEMPTS : logs



\## Mermaid


whk\_YSpXYjYSwQxcYa6ws\_\_nt4y7lPDrJWmAxJyYic17yRM (test API Key)


