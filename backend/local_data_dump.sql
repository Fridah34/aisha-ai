--
-- PostgreSQL database dump
--

\restrict pkskYHyivyU1vyw4bm21i6fs8b7Rh6eMY9Fv3VkWYbuJ9Vs078Ko5ouMWdExvak

-- Dumped from database version 18.4 (Ubuntu 18.4-1.pgdg24.04+1)
-- Dumped by pg_dump version 18.4 (Ubuntu 18.4-1.pgdg24.04+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: postgres
--

SET SESSION AUTHORIZATION DEFAULT;

ALTER TABLE public.alembic_version DISABLE TRIGGER ALL;

COPY public.alembic_version (version_num) FROM stdin;
bf4ed52d9fca
\.


ALTER TABLE public.alembic_version ENABLE TRIGGER ALL;

--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

ALTER TABLE public.users DISABLE TRIGGER ALL;

COPY public.users (id, name, email, hashed_password, google_id, business_name, is_active, created_at, knowledge_base_text, whatsapp_phone_number_id, whatsapp_phone_number, business_type) FROM stdin;
3	Fridah Nthambi	fridahnthambi69@gmail.com	$2b$12$pqWjq/rKhP52LoGPAgIyceEYkJCpi95D8YbL8IaY9t1v1H3BgM6nS	\N	Linfields Shop	t	2026-07-07 15:05:55.652935+03	\N	\N	\N	retail
4	Eve Mipata	evemipata@gmail.com	$2b$12$NltDcmCpSQqgPwiwrrlWbet6QQX6.7TujFy04SInIr9u3O0VAVg8C	\N	Linfilds Shop	t	2026-07-07 15:29:10.238241+03	\N	\N	\N	retail
5	Fridah Nthambi	fridahnthambi@gmail.com	$2b$12$m6QB/GXrA4Md./mFESMXguyIzN24KbJKj5DkCGJvqwjKFNrJlo.7i	\N	Factor	t	2026-07-07 16:04:28.704157+03	\N	\N	\N	retail
1	Test Owner	test@zawadi.com	hashed_placeholder	\N	Zawadi Boutique	t	2026-06-09 15:43:39.871938+03	\N	\N	+254706040948	fashion
2	Test Owner Two	test@kijiji.com	placeholder	\N	Kijiji Hardware	t	2026-06-16 14:40:13.594786+03	\N	\N	\N	retail
6	Levi	lev@gmail.com	$2b$12$OKAVAb/J3nG.yMPGvERm0Ok6o4KG.eCMJzNbhJFcbGhHMggJ/Aswe	\N	Levi's	t	2026-07-09 15:34:44.005643+03	\N	\N	\N	retail
\.


ALTER TABLE public.users ENABLE TRIGGER ALL;

--
-- Data for Name: carts; Type: TABLE DATA; Schema: public; Owner: postgres
--

ALTER TABLE public.carts DISABLE TRIGGER ALL;

COPY public.carts (id, phone_number, business_id, items, updated_at) FROM stdin;
2	+254706040948	1	[]	2026-07-09 14:47:34.570967+03
1	+254706040948	5	[]	2026-07-16 16:46:20.484121+03
\.


ALTER TABLE public.carts ENABLE TRIGGER ALL;

--
-- Data for Name: categories; Type: TABLE DATA; Schema: public; Owner: postgres
--

ALTER TABLE public.categories DISABLE TRIGGER ALL;

COPY public.categories (id, user_id, name, description, display_order, is_active, created_at) FROM stdin;
1	1	Shoes	\N	0	t	2026-07-05 17:57:59.178648+03
3	1	Shawl	\N	0	t	2026-07-05 17:57:59.178648+03
4	1	Skirt	\N	0	t	2026-07-05 17:57:59.178648+03
5	1	Dress	\N	0	t	2026-07-05 17:57:59.178648+03
2	1	Jeans	Khaki pants	0	t	2026-07-05 17:57:59.178648+03
10	5	Shorts	\N	4	t	2026-07-16 14:54:43.67066+03
7	5	Dresses	\N	1	t	2026-07-08 14:15:40.196839+03
8	5	Skirts	\N	2	t	2026-07-08 14:15:52.455562+03
6	5	Shawls	\N	0	t	2026-07-08 14:15:26.797866+03
9	5	Handbags	\N	3	t	2026-07-08 14:16:09.006362+03
\.


ALTER TABLE public.categories ENABLE TRIGGER ALL;

--
-- Data for Name: customers; Type: TABLE DATA; Schema: public; Owner: postgres
--

ALTER TABLE public.customers DISABLE TRIGGER ALL;

COPY public.customers (id, phone_number, name, first_seen, last_seen, is_active, deleted_at, user_id) FROM stdin;
7	+254706040948	Fk	2026-06-15 22:44:25.552163+03	2026-07-16 16:38:01.20202+03	t	\N	1
9	+254706040948	Fk	2026-07-09 13:36:43.288249+03	2026-07-16 16:50:53.564732+03	t	\N	5
\.


ALTER TABLE public.customers ENABLE TRIGGER ALL;

--
-- Data for Name: conversation_states; Type: TABLE DATA; Schema: public; Owner: postgres
--

ALTER TABLE public.conversation_states DISABLE TRIGGER ALL;

COPY public.conversation_states (id, customer_id, user_id, status, taken_over_at, resolved_at, updated_at, pending_action, selected_business_id, selected_category_id, selected_business_type) FROM stdin;
6	7	1	ai_active	2026-07-02 15:39:39.223075+03	2026-07-03 14:55:29.080252+03	2026-07-06 13:34:27.756828+03	\N	\N	\N	\N
7	9	5	human_active	2026-07-16 16:51:53.49275+03	2026-07-10 22:24:28.681716+03	2026-07-16 16:51:53.478646+03	\N	\N	\N	\N
\.


ALTER TABLE public.conversation_states ENABLE TRIGGER ALL;

--
-- Data for Name: conversations; Type: TABLE DATA; Schema: public; Owner: postgres
--

ALTER TABLE public.conversations DISABLE TRIGGER ALL;

COPY public.conversations (id, customer_id, user_id, sender, message_text, "timestamp", language, delivery_status) FROM stdin;
191	7	1	customer	Habari	2026-06-27 09:51:26.690985+03	sw	\N
193	7	1	customer	uko na trousers?	2026-06-27 09:52:08.239234+03	en	\N
195	7	1	customer	sawa nipe moja	2026-06-27 09:52:48.889969+03	sw	\N
197	7	1	customer	asanti	2026-06-27 09:55:31.677687+03	en	\N
199	7	1	customer	Hey	2026-06-27 10:34:50.344678+03	en	\N
204	7	1	assistant	Your total for 1 pair of Zara Ladies Heels is Ksh 3000. Please pay via M-Pesa to our business number. We will contact you once payment is confirmed. What's your name, please?	2026-06-27 10:35:42.153596+03	en	\N
192	7	1	assistant	Habari nzuri! Ninafurahi kuwa umepata mahitaji yako. Ikiwa unahitaji chochote zaidi, usihese kuuliza.	2026-06-27 09:51:27.197973+03	sw	\N
194	7	1	assistant	Tunayo Wide legged trousers za levi's, zinazogharimu Ksh 2500. Ziko katika saizi Large, na zimefanywa kwa nyenzo ya cotton.	2026-06-27 09:52:08.643251+03	sw	\N
196	7	1	assistant	Jumla ya agizo lako ni Ksh 2500 kwa Wide legged trousers. Tafadhali lipa kwa njia ya M-Pesa kwa nambari ya biashara yetu. Tutakuunganishia kwa ajili ya kujifungua baada ya malipo kuwekwa.	2026-06-27 09:52:49.290797+03	sw	\N
198	7	1	assistant	Karibu! Tutakuhabari kuhusu utoaji wa agizo lako.	2026-06-27 09:55:32.080606+03	sw	\N
200	7	1	assistant	Hello! How can I help you today?	2026-06-27 10:34:50.794041+03	en	\N
201	7	1	customer	do you have heels	2026-06-27 10:35:13.304005+03	en	\N
83	7	1	customer	Hello, do you have shoes?	2026-06-15 22:44:25.584672+03	en	\N
84	7	1	assistant	Yes, we have shoes. We currently have Nike Air Force 1, Adidas Samba, and Puma Suede Classic in stock. Which one are you interested in?	2026-06-15 22:44:26.291982+03	en	\N
85	7	1	customer	Hello, do you have shoes?	2026-06-15 22:47:29.164023+03	en	\N
86	7	1	assistant	We have Nike Air Force 1, Adidas Samba, and Puma Suede Classic in stock. Which one are you interested in?	2026-06-15 22:47:29.869189+03	en	\N
91	7	1	customer	Good Night	2026-06-15 23:01:47.841964+03	en	\N
92	7	1	assistant	Good night, have a great rest.	2026-06-15 23:01:48.727454+03	en	\N
93	7	1	customer	Hello,do you have shoes?	2026-06-16 11:28:11.540835+03	en	\N
94	7	1	assistant	We have Nike Air Force 1, Adidas Samba, and Puma Suede Classic in stock. Which one are you interested in?	2026-06-16 11:28:12.400621+03	en	\N
95	7	1	customer	Habari, mna viatu?	2026-06-16 11:28:49.128569+03	sw	\N
96	7	1	assistant	Tuna viatu vya Nike Air Force 1, Adidas Samba, na Puma Suede Classic. Unahitaji aina gani?	2026-06-16 11:28:50.044204+03	sw	\N
97	7	1	customer	how much is the Nike Air Force 1?	2026-06-16 11:29:28.666706+03	en	\N
98	7	1	assistant	The Nike Air Force 1 costs KSh 4500.0 and is available in red and white, sizes 6-11.	2026-06-16 11:29:29.380705+03	en	\N
99	7	1	customer	I want to order Nike size 8	2026-06-16 11:30:00.208253+03	sw	\N
100	7	1	assistant	Your total comes to KSh 4500.0. May I have your name, please?	2026-06-16 11:30:00.923804+03	en	\N
101	7	1	customer	Fridah	2026-06-16 11:30:19.809724+03	en	\N
102	7	1	assistant	Thank you, Fridah. To complete your order, please pay KSh 4500.0 via M-Pesa to our business number. We will contact you once we receive the payment.	2026-06-16 11:30:20.528069+03	en	\N
103	7	1	customer	okay thank you	2026-06-16 11:30:43.6932+03	en	\N
104	7	1	assistant	You're welcome, Fridah. We'll be in touch soon. Have a great day!	2026-06-16 11:30:44.406507+03	en	\N
105	7	1	customer	Can I get a bulk discount for 100 pairs?	2026-06-16 11:36:37.390513+03	en	\N
106	7	1	assistant	Let me connect you with our team.	2026-06-16 11:36:38.12676+03	en	\N
107	7	1	customer	Can I get a bulk discount for 100 pairs?	2026-06-16 11:56:20.293071+03	en	\N
108	7	1	assistant	Let me connect you with our team.	2026-06-16 11:56:21.022265+03	en	\N
109	7	1	customer	Can I get a bulk discount for 100 pairs?	2026-06-16 12:15:48.925071+03	en	\N
110	7	1	assistant	Let me connect you with our team.	2026-06-16 12:15:49.643985+03	en	\N
111	7	1	customer	Hi, what dresses do you have?	2026-06-16 14:50:42.173356+03	en	\N
112	7	1	assistant	We have an Ankara Dress available, hand-stitched and made from ankara fabric, priced at KSh 2500.0, in sizes S-XL. \nWould you like to place an order?	2026-06-16 14:50:42.966483+03	en	\N
113	7	1	customer	what's the price of Ankara dress?	2026-06-16 14:59:22.395383+03	en	\N
114	7	1	assistant	The price of the Ankara dress is KSh 2500.0. \nWould you like to place an order?	2026-06-16 14:59:23.130127+03	en	\N
115	7	1	customer	what's the price of Ankara dress?	2026-06-16 15:01:17.541681+03	en	\N
116	7	1	assistant	I don't have information on the price of an Ankara dress. We have shoes like Adidas Samba, Puma Suede Classic, and Nike Air Force 1. \nLet me connect you with our team.	2026-06-16 15:01:18.260214+03	en	\N
87	7	1	customer	Hello, do you have shoes?	2026-06-15 22:55:06.221276+03	en	\N
88	7	1	assistant	Yes, we have shoes. We currently have Nike Air Force 1, Adidas Samba, and Puma Suede Classic in stock. Which one are you interested in?	2026-06-15 22:55:09.966232+03	en	\N
89	7	1	customer	Hello, do you have shoes?	2026-06-15 22:56:32.308576+03	en	\N
90	7	1	assistant	Yes, we have shoes from Nike, Adidas, and Puma. Would you like to know more about our available styles?	2026-06-15 22:56:33.043629+03	en	\N
117	7	1	customer	what's the price of the Ankara	2026-06-17 12:32:35.071818+03	en	\N
118	7	1	assistant	Samahani, kuna tatizo kidogo. Tafadhali jaribu tena baadaye.Sorry, we are experiencing a brief issue. Please try again shortly.	2026-06-17 12:32:44.347385+03	sw	\N
119	7	1	customer	What's the price of the Ankara dress?	2026-06-17 12:34:25.397272+03	en	\N
120	7	1	assistant	We don't have an Ankara dress listed in our products. Let me connect you with our team for more information.	2026-06-17 12:34:27.537455+03	en	\N
121	7	1	customer	What products do you have?	2026-06-17 13:08:44.918694+03	en	\N
122	7	1	assistant	We have an Ankara Dress available, priced at KSh 3200.0, in sizes S-XL. Would you like to know more or place an order?	2026-06-17 13:08:45.624579+03	en	\N
123	7	1	customer	do you have an Ankara blouse?	2026-06-18 13:39:01.418838+03	en	\N
124	7	1	assistant	We currently have an Ankara Dress available for KSh 3200.0. However, I don't have information on an Ankara blouse. Let me connect you with our team for that.	2026-06-18 13:39:02.249446+03	en	\N
125	7	1	human	Hello, this is a test reply	2026-06-19 22:59:44.37206+03	en	\N
126	7	1	human	At the moment it is not in our catalogue	2026-06-19 23:00:50.68902+03	en	\N
127	7	1	human	hey	2026-06-19 23:10:36.319346+03	en	\N
128	7	1	human	At the moment it is not in our catalogue	2026-06-19 23:16:29.745147+03	en	\N
129	7	1	customer	Good Afternoon	2026-06-23 12:33:23.48015+03	en	\N
130	7	1	assistant	Good afternoon. Welcome to Zawadi Boutique. How can I assist you today?	2026-06-23 12:33:24.35861+03	en	\N
131	7	1	customer	Do you have heels?	2026-06-23 12:33:46.612451+03	en	\N
132	7	1	assistant	We have Zara Ladies Heels, 6-inch high heels with a pointed tip, available for Ksh 3000. Would you like to purchase a pair?	2026-06-23 12:33:47.089817+03	en	\N
133	7	1	customer	oh that's great.i would like 2 pairs	2026-06-23 12:34:20.041604+03	en	\N
134	7	1	assistant	I confirm you want 2 pairs of Zara Ladies Heels. Your total comes to Ksh 6000. May I have your name, please?	2026-06-23 12:34:20.53213+03	en	\N
135	7	1	customer	My name is Jane	2026-06-23 12:34:39.148544+03	en	\N
138	7	1	assistant	You're welcome, Jane. Your order is now placed, and we'll be in touch soon. Have a great day!	2026-06-23 12:35:09.328257+03	en	\N
202	7	1	assistant	Yes, we have Zara Ladies Heels, size 38, black, for Ksh 3000. I can suggest pairing them with a mini black Zara handbag for Ksh 2500. Would you like to buy the heels?	2026-06-27 10:35:13.705025+03	en	\N
203	7	1	customer	yes one pair	2026-06-27 10:35:41.753142+03	en	\N
136	7	1	assistant	Hi Jane, your total for 2 pairs of Zara Ladies Heels is Ksh 6000. To complete your order, please pay via M-Pesa to our business number. I'll confirm your order once payment is made and we'll be in touch.	2026-06-23 12:34:39.636403+03	en	\N
137	7	1	customer	Okay thank you so much	2026-06-23 12:35:08.853941+03	en	\N
140	7	1	assistant	Thank you, Jane. Have a wonderful day and we look forward to serving you again.	2026-06-23 12:35:30.655007+03	en	\N
139	7	1	customer	You too	2026-06-23 12:35:30.157352+03	en	\N
141	7	1	customer	Do you have silk skirts?	2026-06-24 12:44:56.760595+03	en	\N
142	7	1	assistant	Yes, we have silk skirts available in sizes S, M, L, and XL, priced at Ksh 1500 per piece. I can suggest pairing it with a white tank top retailing at 1000. Would you like to purchase one?	2026-06-24 12:44:57.273759+03	en	\N
143	7	1	customer	Do you have silk skirts in your shop?	2026-06-24 12:54:56.501814+03	en	\N
144	7	1	assistant	Yes, we have silk skirts in sizes S, M, L, and XL, priced at Ksh 1500 per piece. Would you like to buy one?	2026-06-24 12:54:57.025888+03	en	\N
145	7	1	customer	yes i would 3 pieces two large and one XL .	2026-06-24 12:55:54.55677+03	en	\N
146	7	1	assistant	You'd like to buy 3 silk skirts: 2 Large and 1 XL, totaling Ksh 4500. May I know your name, please?	2026-06-24 12:55:55.068173+03	en	\N
147	7	1	customer	Kioko	2026-06-24 12:56:41.478636+03	en	\N
148	7	1	assistant	Thank you, Kioko. Your total comes to Ksh 4500. To complete the order, please pay via M-Pesa to our business number. I'll confirm your order and we'll be in touch.	2026-06-24 12:56:41.989129+03	en	\N
149	7	1	customer	okay thank you	2026-06-24 12:57:09.060425+03	en	\N
150	7	1	assistant	Your order is confirmed, Kioko. We'll be in touch soon. Have a great day!	2026-06-24 12:57:09.590464+03	en	\N
151	7	1	customer	You too!	2026-06-24 12:57:29.332797+03	en	\N
152	7	1	assistant	You're welcome, Kioko. Enjoy your silk skirts!	2026-06-24 12:57:29.85453+03	en	\N
153	7	1	customer	Do you have heels?	2026-06-24 13:18:44.901604+03	en	\N
154	7	1	assistant	Yes, we have Zara Ladies Heels, size 38, black, priced at Ksh 3000 per pair. Would you like to buy a pair?	2026-06-24 13:18:45.38717+03	en	\N
155	7	1	customer	yes i would like one	2026-06-24 13:19:10.59746+03	en	\N
156	7	1	assistant	The total for the Zara Ladies Heels is Ksh 3000. I recommend pairing it with a mini black Zara handbag for Ksh 2500. Would you like to add the handbag to your order, Kioko?	2026-06-24 13:19:11.072837+03	en	\N
157	7	1	customer	hey	2026-06-24 14:09:42.869958+03	en	\N
158	7	1	assistant	Hello, how can I help you today?	2026-06-24 14:09:43.362989+03	en	\N
159	7	1	customer	do you have heels?	2026-06-24 14:09:59.892587+03	en	\N
160	7	1	assistant	Yes, we have Zara Ladies Heels, size 38, black, priced at Ksh 3000 per pair. Would you like to buy a pair?	2026-06-24 14:10:00.377079+03	en	\N
161	7	1	customer	yes one pair	2026-06-24 14:10:25.379538+03	en	\N
162	7	1	assistant	To confirm, you'd like to buy 1 pair of Zara Ladies Heels, size 38, black, for Ksh 3000. May I have your name, please?	2026-06-24 14:10:25.888138+03	en	\N
163	7	1	customer	Fridah	2026-06-24 14:12:08.863115+03	en	\N
164	7	1	customer	Do you have heels?	2026-06-24 14:23:40.672154+03	en	\N
165	7	1	customer	Do you have heels?	2026-06-24 14:27:57.841269+03	en	\N
166	7	1	assistant	Yes, we have Zara Ladies Heels, size 38, black, priced at Ksh 3000 per pair. You had previously selected a pair, Fridah. Would you like to proceed with the order?	2026-06-24 14:28:00.15109+03	en	\N
167	7	1	customer	yes i would like to proceed with the order	2026-06-24 14:28:37.394055+03	sw	\N
168	7	1	assistant	Your total comes to Ksh 3000. Please pay via M-Pesa to our business number. I'll confirm your order and we'll be in touch.	2026-06-24 14:28:37.86205+03	en	\N
169	7	1	customer	do you have heels?	2026-06-24 15:26:32.120583+03	en	\N
170	7	1	assistant	We have Zara Ladies Heels, size 38, black, priced at Ksh 3000 per pair. You already have an order for this item, Fridah. Would you like to add another pair?	2026-06-24 15:26:32.864706+03	en	\N
171	7	1	customer	No ,just that one pair	2026-06-24 15:27:04.220875+03	en	\N
172	7	1	assistant	Your order is confirmed: 1 pair of Zara Ladies Heels, size 38, black, for Ksh 3000. We will contact you for delivery after payment.	2026-06-24 15:27:04.701409+03	en	\N
173	7	1	customer	can i see an image of the heels?	2026-06-24 15:27:30.81965+03	en	\N
174	7	1	assistant	I'm a text-based assistant and don't have the capability to share images. Let me connect you with our team for that.	2026-06-24 15:27:31.310023+03	en	\N
175	7	1	customer	hey	2026-06-26 11:57:40.908279+03	en	\N
176	7	1	assistant	Hello, welcome to Zawadi Boutique. How can I help you today?	2026-06-26 11:57:41.423875+03	en	\N
177	7	1	customer	I want to order heels .Are they available?	2026-06-26 11:58:50.969694+03	sw	\N
178	7	1	assistant	We have Zara Ladies Heels available, size 38, black, for Ksh 3000. Would you like to proceed with the order?	2026-06-26 11:58:51.430284+03	en	\N
179	7	1	customer	I would like two pairs kindly	2026-06-26 11:59:32.14288+03	en	\N
180	7	1	assistant	We have two pairs of Zara Ladies Heels available for you. The total cost will be Ksh 6000. May I have your name, please?	2026-06-26 11:59:32.603554+03	en	\N
181	7	1	customer	My name is Nthambi	2026-06-26 12:00:02.825456+03	en	\N
182	7	1	assistant	Hi Nthambi, to complete your order, please pay Ksh 6000 via M-Pesa to our business number. Once paid, we'll contact you for delivery.	2026-06-26 12:00:03.285435+03	en	\N
183	7	1	customer	hey	2026-06-26 13:56:08.828795+03	en	\N
184	7	1	assistant	Hi again, Nthambi! Your order for two pairs of Zara Ladies Heels is still on. Is there something else I can help you with?	2026-06-26 13:56:09.59686+03	en	\N
185	7	1	customer	do you have handbags also	2026-06-26 13:56:45.615107+03	en	\N
186	7	1	assistant	We have a mini black Zara handbag that pairs well with the Zara Ladies Heels, retailing at Ksh 2500. Would you like to add it to your order?	2026-06-26 13:56:46.090516+03	en	\N
187	7	1	customer	yes please	2026-06-26 13:57:02.561435+03	en	\N
188	7	1	assistant	Your new total is Ksh 8500 (2 pairs of heels + mini handbag). Please pay via M-Pesa to our business number. We'll contact you for delivery once paid.	2026-06-26 13:57:03.04578+03	en	\N
189	7	1	customer	okay thank you	2026-06-26 13:57:26.977448+03	en	\N
190	7	1	assistant	You're welcome, Nthambi! We'll be in touch soon to arrange delivery of your order. Have a great day!	2026-06-26 13:57:27.477792+03	en	\N
205	7	1	customer	Good morning	2026-06-30 11:48:20.721805+03	en	\N
206	7	1	assistant	Good morning! Welcome to Zawadi Boutique. How can I help you today?	2026-06-30 11:48:21.267413+03	en	\N
207	7	1	customer	do you have jorts in your shop?	2026-06-30 11:48:59.050154+03	en	\N
208	7	1	assistant	We have wide legged trousers, but not specifically jorts. Would you like to know more about the wide legged trousers we have?	2026-06-30 11:48:59.567298+03	en	\N
209	7	1	customer	okay tell me more	2026-06-30 11:49:35.883113+03	en	\N
210	7	1	assistant	Our wide legged trousers are from Levi's, made of cotton fabric, and are available in Large size. They cost Ksh 2500. Would you like to proceed with purchasing or know more about other products?	2026-06-30 11:49:36.39374+03	en	\N
211	7	1	customer	okay but i wanted jorts.so i will not be proceeding with an order	2026-06-30 11:50:23.133746+03	sw	\N
212	7	1	assistant	Let me connect you with our team for that.	2026-06-30 11:50:23.65426+03	en	\N
213	7	1	human	Currently we do not have jorts but we will be restocking them in the next two weeks you can come back and enquire about them. Thank happy shopping at Zawadi boutique	2026-06-30 11:55:14.761184+03	en	delivered
214	7	1	customer	Do you have tank tops?	2026-06-30 13:29:54.097409+03	en	\N
215	7	1	customer	Do you have tank tops?	2026-06-30 13:31:16.772563+03	en	\N
216	7	1	assistant	We have a white tank top that pairs well with our Silk Skirt, and it retails at Ksh 1000. Would you like to know more?	2026-06-30 13:31:17.523708+03	en	\N
217	7	1	customer	tell me more	2026-06-30 13:31:48.132743+03	en	\N
218	7	1	assistant	Our white tank top is a simple, versatile piece that can be paired with many of our products, including the Silk Skirt. It's available in various sizes, but I can confirm the price is Ksh 1000. Would you like to purchase it or pair it with the Silk Skirt?	2026-06-30 13:31:48.613375+03	en	\N
219	7	1	customer	yes i want one pair. Do you have leather jackets as well?	2026-06-30 13:32:34.926568+03	en	\N
220	7	1	assistant	I can confirm your order for the white tank top. However, we don't have leather jackets in our current product list.	2026-06-30 13:32:35.406749+03	en	\N
221	7	1	customer	do you have skorts in your shop?	2026-06-30 13:41:15.695178+03	en	\N
222	7	1	assistant	We don't have skorts in our current product list. However, we do have a Silk Skirt available, which I mentioned earlier. Would you like to proceed with your tank top order or explore other available products?	2026-06-30 13:41:16.427898+03	en	\N
223	7	1	customer	No only that	2026-06-30 13:43:01.321839+03	en	\N
224	7	1	assistant	Your total for the white tank top is Ksh 1000. Please pay via M-Pesa to our business number. We will contact you once payment is confirmed. \n\n[No handover tag as AISHA handled this completely]	2026-06-30 13:43:01.813909+03	en	\N
225	7	1	customer	hey dou have mummy jeans	2026-06-30 14:16:33.002475+03	en	\N
226	7	1	assistant	We have Wide legged trousers, but not specifically "mummy jeans". The Wide legged trousers are Levi's, made of cotton fabric, and are available in Large size for Ksh 2500. Would you like to know more?	2026-06-30 14:16:33.496193+03	en	\N
227	7	1	customer	okay how can i get mummy jeans	2026-06-30 14:17:32.533627+03	en	\N
228	7	1	assistant	Let me connect you with our team for that.	2026-06-30 14:17:33.010495+03	en	\N
229	7	1	customer	okay	2026-07-02 12:56:09.974369+03	en	\N
230	7	1	human	notat teh moment	2026-07-02 15:36:39.40349+03	en	delivered
231	7	1	customer	hey	2026-07-02 15:36:58.09882+03	en	\N
232	7	1	assistant	Hello! Welcome to Zawadi Boutique. How can I help you today?	2026-07-02 15:36:58.87728+03	en	\N
233	7	1	customer	do you have skirts?	2026-07-02 15:37:37.315462+03	en	\N
234	7	1	assistant	Yes, we do! We have a lovely Silk Skirt available in sizes S, M, L, and XL for Ksh 1500 per piece.	2026-07-02 15:37:37.855213+03	en	\N
235	7	1	customer	okay i would like one pair	2026-07-02 15:38:43.441999+03	en	\N
236	7	1	assistant	Great! Just to confirm, you would like one Silk Skirt, correct? It retails for Ksh 1500.	2026-07-02 15:38:44.041327+03	en	\N
237	7	1	customer	yes	2026-07-02 15:39:04.327222+03	en	\N
238	7	1	assistant	Excellent! May I have your name, please? Your total for one Silk Skirt will be Ksh 1500. You can pay via M-Pesa to our business number.	2026-07-02 15:39:03.793693+03	en	\N
239	7	1	customer	do you also have vests?	2026-07-02 15:39:12.779809+03	en	\N
240	7	1	assistant	I'm sorry, I don't have information about vests in my current product list. Let me connect you with our team who can help you with that.	2026-07-02 15:39:13.313984+03	en	\N
241	7	1	customer	Good Afternoon	2026-07-03 13:21:39.612014+03	en	\N
242	7	1	customer	Good Afternoon	2026-07-03 15:06:16.478794+03	en	\N
243	7	1	assistant	Good afternoon! Welcome to Zawadi Boutique. How can I assist you today?	2026-07-03 15:06:17.708659+03	en	\N
244	7	1	customer	Good morning	2026-07-06 12:05:46.852562+03	en	\N
245	7	1	assistant	Good morning! How can I assist you today?	2026-07-06 12:05:47.447691+03	en	\N
246	7	1	customer	i would like to shop from your shop	2026-07-06 12:12:20.545863+03	en	\N
247	7	1	customer	I would like to shop from your boutique	2026-07-06 12:16:46.989777+03	en	\N
248	7	1	assistant	That's wonderful! I'd love to help you shop!\n\nHowever, I must clarify that **I am an AI assistant and don't actually have a physical boutique or an online store with items to sell directly.**\n\nBut I *can absolutely act as your personal shopper and fashion consultant!**\n\nTell me:\n*   **What kind of items are you looking for?** (e.g., a dress, a new outfit for work, accessories, gifts)\n*   **What's your preferred style?** (e.g., casual, elegant, bohemian, modern, classic)\n*   **Is there a specific occasion you're shopping for?**\n*   **Do you have a particular budget in mind?**\n*   **Are you looking for recommendations for online stores, local shops, or just general style advice?**\n\nLet's "shop" together and find you some fantastic ideas!	2026-07-06 12:16:47.780919+03	en	\N
249	7	1	customer	what products do you have ?	2026-07-06 12:17:56.666976+03	en	\N
250	7	1	assistant	Ah, that's a great question, and it highlights an important distinction!\n\nAs an AI, I don't physically **have** products in the way a traditional shop does. I don't manufacture, stock, or ship items like clothing, accessories, or home goods.\n\nHowever, if you think of "products" as **services, information, and recommendations**, then I have quite a few! My "products" are:\n\n1.  **Style Advice & Outfit Ideas:**\n    *   Recommendations for outfits for specific occasions (weddings, work, casual, parties).\n    *   Tips on how to mix and match items you already own.\n    *   Guidance on current fashion trends.\n    *   Advice on flattering styles for different body types.\n\n2.  **Product Recommendations (from other stores):**\n    *   I can suggest specific types of clothing, accessories, or beauty products.\n    *   I can help you find items based on your preferences (e.g., "sustainable brands," "petite sizing," "vintage-inspired dresses").\n    *   I can describe what kind of items would suit your needs or style.\n\n3.  **Brand Information & Shopping Guidance:**\n    *   Information about different fashion brands, their aesthetics, and price points.\n    *   Suggestions for online retailers or types of physical stores where you might find what you're looking for.\n    *   Help comparing different items or brands.\n\n4.  **Fashion Education:**\n    *   Explaining fabric types, garment construction, or care instructions.\n    *   Defining fashion terms or styles.\n\n5.  **Personalized Shopping Assistant:**\n    *   I can act as your virtual shopper, helping you narrow down choices, articulate your needs, and brainstorm ideas.\n    *   I can help you create a shopping list or wish list.\n\nSo, while I don't have a catalog of items to *sell* you, I have an extensive "catalog" of information and assistance to help you *find and choose* the perfect products from real-world stores!\n\nWhat kind of "product" (service or information) can I offer you today? Tell me what you're looking for!	2026-07-06 12:17:57.195219+03	sw	\N
251	7	1	customer	i would like to shop from your boutique	2026-07-06 12:53:07.885471+03	en	\N
296	9	5	customer	I'm interested in the Ankara Dress	2026-07-10 22:40:38.871108+03	en	\N
297	9	5	assistant	The Ankara Dress is a beautiful piece, available in sizes S, M, L, XL, and XXL. It's priced at Ksh 2500. Would you like to proceed with an order?	2026-07-10 22:40:39.406984+03	en	\N
298	9	5	customer	yes	2026-07-10 22:41:18.005013+03	en	\N
252	7	1	assistant	Thank you so much for your enthusiasm! I truly appreciate it.\n\nI think there might still be a slight misunderstanding, and I apologize if my previous explanations weren't clear enough.\n\n**I am an AI assistant, and I don't actually own or operate a physical boutique or an online store with products to sell directly.** I don't have shelves of clothes, accessories, or anything physical.\n\nMy "boutique" is entirely virtual – it's full of information, ideas, and advice! Think of me as your personal, knowledgeable, and always-available **virtual shopping assistant, stylist, and fashion consultant.**\n\n**While I can't sell you items myself, I can absolutely help you:**\n\n*   **Discover new brands and shops** (online or in your area).\n*   **Find specific types of items** (e.g., "a flowy summer dress," "comfortable work shoes," "unique jewelry").\n*   **Curate outfit ideas** based on your style, occasion, and budget.\n*   **Provide recommendations** for items that suit your preferences.\n*   **Help you understand trends, fabrics, and styling tips.**\n\nSo, let's pretend my "boutique" is a vast, invisible catalog of all the fashion knowledge and shopping possibilities out there!\n\n**To help me "shop" for you virtually, please tell me:**\n\n*   **What kind of items are you dreaming of?**\n*   **What's your personal style like?**\n*   **Is there a special occasion coming up?**\n*   **What's your budget range?**\n\nLet's make some wonderful shopping discoveries together!	2026-07-06 12:53:06.603238+03	en	\N
253	7	1	customer	i would like to shop	2026-07-06 13:17:35.342231+03	en	\N
254	7	1	assistant	Great! I can definitely help you with that. To get started, what kind of shopping are you looking to do today?\n\nAre you looking for:\n\n*   **Clothing, fashion, or accessories?**\n*   **Electronics or gadgets?**\n*   **Home goods, decor, or furniture?**\n*   **Groceries or food items?**\n*   **Gifts for someone?**\n*   **Books, movies, or music?**\n*   **Health and beauty products?**\n*   **Or something else entirely?**\n\nOnce I know what you're interested in, we can narrow it down! Tell me more about what you have in mind.\n\nAlso, consider these questions, and let me know the answers if you have them:\n\n*   **Online or in-store?**\n*   **Do you have a specific item or brand in mind, or are you just browsing for ideas?**\n*   **What's your approximate budget?**\n*   **Are you looking for any deals or discounts?**\n*   **If in-store, what's your general location?**\n\nThe more details you give me, the better I can assist you!	2026-07-06 13:17:35.877676+03	en	\N
255	7	1	customer	i would like to shop	2026-07-06 13:27:24.405019+03	en	\N
256	7	1	customer	i would like to shop	2026-07-06 13:30:27.717224+03	en	\N
257	7	1	customer	i would like to shop	2026-07-06 13:31:16.35497+03	en	\N
258	7	1	assistant	Sure! Here are our categories:\n\nWhich category are you shopping for today? 🛍️\n\n1 *Dress*\n2 *Jeans*\n3 *Shawl*\n4 *Shoes*\n5 *Skirt*\n\nJust reply with a number or the category name.	2026-07-06 13:31:25.529425+03	en	\N
259	7	1	customer	i would like to shop	2026-07-06 13:33:59.216057+03	en	\N
260	7	1	assistant	Wonderful! I can definitely help you shop. Here are our categories:\n\nWhich category are you shopping for today? 🛍️\n\n1 *Dress*\n2 *Jeans*\n3 *Shawl*\n4 *Shoes*\n5 *Skirt*\n\nJust reply with a number or the category name.	2026-07-06 13:34:11.479717+03	en	\N
261	7	1	customer	1	2026-07-06 13:34:27.241736+03	en	\N
262	7	1	assistant	Here's what we have:\n\n• *Ankara Dress* — Ksh 3200.00\n\nWant details on any of these, or ready to order?	2026-07-06 13:34:27.781224+03	en	\N
263	7	1	customer	details	2026-07-06 13:34:42.70009+03	en	\N
264	7	1	assistant	The Ankara Dress is Ksh 3200. It's an African-themed orange, hand-stitched ankara fabric dress, available in sizes L-XL. It is a size 10.\n\nWould you like to purchase it, or perhaps browse something else?	2026-07-06 13:34:43.222039+03	en	\N
265	7	1	customer	browse something else	2026-07-06 13:35:02.735746+03	en	\N
266	7	1	assistant	No problem at all! Which category would you like to explore next?\n\n1 *Dress*\n2 *Jeans*\n3 *Shawl*\n4 *Shoes*\n5 *Skirt*\n\nJust tell me the number or the category name.	2026-07-06 13:35:03.258241+03	en	\N
267	9	5	customer	do you have dresses?	2026-07-09 13:36:43.328821+03	en	\N
268	9	5	assistant	Samahani, kuna tatizo kidogo. Tafadhali jaribu tena baadaye. Sorry, we are experiencing a brief issue. Please try again shortly.	2026-07-09 13:36:43.868525+03	sw	\N
269	9	5	customer	do you have dresses?	2026-07-09 13:51:59.254526+03	en	\N
270	9	5	assistant	Samahani, kuna tatizo kidogo. Tafadhali jaribu tena baadaye. Sorry, we are experiencing a brief issue. Please try again shortly.	2026-07-09 13:51:59.758847+03	sw	\N
271	9	5	customer	do you have dresses?	2026-07-09 14:06:48.384939+03	en	\N
272	9	5	assistant	Yes, we do! We have the Ankara Dress available. Would you like to know more about it?	2026-07-09 14:06:48.899614+03	en	\N
273	9	5	customer	yes please	2026-07-09 14:07:30.416492+03	en	\N
274	9	5	assistant	Great! We have the Ankara Dress for Ksh 2500 per piece. It's available in sizes S, M, L, XL, and XXL.	2026-07-09 14:07:30.92505+03	en	\N
275	9	5	customer	i would like one pair in size small and another in xl	2026-07-09 14:08:09.961274+03	en	\N
276	9	5	assistant	Understood! That would be one Ankara Dress in size Small and another in size XL. The total for two dresses will be Ksh 5000.\n\nWould you like to proceed with this order?	2026-07-09 14:08:10.461017+03	en	\N
277	9	5	customer	yes	2026-07-09 14:08:33.222215+03	en	\N
278	9	5	assistant	Wonderful! To finalize your order, could you please share your name and a contact number? Once I have those details, I'll pass everything to our team to arrange delivery.	2026-07-09 14:08:33.724306+03	sw	\N
279	9	5	customer	Fridah  my number is  0745214845	2026-07-09 14:09:31.200298+03	en	\N
280	9	5	assistant	Thank you, Fridah! I've noted your order for one Ankara Dress in size Small and another in size XL, and I've passed your details (Fridah, 0745214845) to our team.\n\nYour total is Ksh 5000. Please pay via M-Pesa to our business number. Our team will contact you shortly to confirm payment and delivery details!	2026-07-09 14:09:31.705148+03	en	\N
281	7	1	customer	for a shawl	2026-07-09 15:15:26.809812+03	en	\N
282	7	1	assistant	We have a beautiful Pashmina shawl for Ksh 1500. It's a medium-sized, red, woven Pakistan shawl scarf.	2026-07-09 15:15:27.374535+03	en	\N
283	9	5	customer	2	2026-07-10 17:13:36.579484+03	en	\N
284	9	5	assistant	Sorry, could you please type your question?	2026-07-10 17:13:37.097704+03	en	\N
285	9	5	customer	2	2026-07-10 21:16:09.4744+03	en	\N
286	9	5	assistant	Sorry, could you please type your question? I'm here to help with any inquiries about our products.	2026-07-10 21:16:09.984807+03	en	\N
287	9	5	customer	1	2026-07-10 21:22:16.25854+03	en	\N
288	9	5	assistant	Sorry, could you please type your question? I'm here to help with any inquiries about our products.	2026-07-10 21:22:17.258204+03	en	\N
289	9	5	customer	1	2026-07-10 22:14:09.886118+03	en	\N
290	9	5	assistant	Sorry, could you please type your question? I'm here to help with any inquiries about our products.	2026-07-10 22:14:10.388383+03	en	\N
291	9	5	customer	1	2026-07-10 22:15:09.493394+03	en	\N
292	9	5	assistant	Sorry, I didn't understand that. Could you please type your question?	2026-07-10 22:15:10.010173+03	en	\N
293	9	5	customer	1	2026-07-10 22:23:14.909881+03	en	\N
294	9	5	customer	1	2026-07-10 22:24:46.485942+03	en	\N
295	9	5	assistant	Sorry, could you please type your question? I'm here to help with any inquiries about our products.	2026-07-10 22:24:47.00469+03	en	\N
299	9	5	assistant	To confirm your order, may I have your name and contact information, please?	2026-07-10 22:41:18.4975+03	en	\N
300	9	5	customer	Fridah my contact is 0767384512	2026-07-13 10:25:38.890973+03	en	\N
301	9	5	assistant	Thank you, Fridah! I've passed on your details to our team. They'll be in touch with you regarding your order.	2026-07-13 10:25:39.732512+03	en	\N
302	9	5	customer	Hey	2026-07-14 10:21:50.214636+03	en	\N
303	9	5	assistant	Hello! Welcome to Factor. How can I help you today?	2026-07-14 10:21:50.756594+03	en	\N
304	9	5	customer	hey	2026-07-14 11:43:43.001676+03	en	\N
305	9	5	assistant	Hello! Welcome to Factor. How can I help you today?	2026-07-14 11:43:43.627079+03	en	\N
306	9	5	customer	Ankara	2026-07-15 14:44:16.843637+03	en	\N
307	9	5	customer	Ankara	2026-07-15 14:44:17.451866+03	en	\N
308	9	5	assistant	Our Ankara Dress is Ksh 2500.0 per piece, available in sizes S, M, L, XL, and XXL. Would you like to order one?	2026-07-15 14:44:17.960549+03	en	\N
309	9	5	customer	Yes i would like order	2026-07-15 14:44:49.544868+03	sw	\N
310	9	5	customer	Yes i would like order	2026-07-15 14:44:50.039337+03	sw	\N
311	9	5	assistant	To confirm your order, may I have your name and contact number, please?	2026-07-15 14:44:50.525127+03	en	\N
312	9	5	customer	Factor	2026-07-15 16:22:04.051666+03	en	\N
313	9	5	assistant	Welcome to Factor! Here's what we have in Dress: Ankara Dress, chiffon dress 👇\n\nReply with a product name to see more and order.\n\n_Tip: reply 'menu' anytime to browse other stores._	2026-07-15 16:22:06.65887+03	en	\N
314	9	5	customer	Ankara	2026-07-15 16:22:36.404002+03	en	\N
315	9	5	assistant	Great choice! *Ankara Dress* — Ksh 2500.00\nSIze: S,M,L,XL,XXL\n\nWhich one would you like?	2026-07-15 16:22:36.942377+03	en	\N
316	9	5	customer	m	2026-07-15 22:27:02.713834+03	en	\N
317	9	5	assistant	How many would you like?	2026-07-15 22:27:03.58639+03	en	\N
318	9	5	customer	only 1	2026-07-15 22:27:20.027187+03	en	\N
319	9	5	assistant	Please reply with just a number, e.g. 2	2026-07-15 22:27:20.503706+03	en	\N
320	9	5	customer	1	2026-07-15 22:27:32.976957+03	en	\N
321	9	5	assistant	Added: 1x Ankara Dress — Ksh 2500.00\n\nYour cart:\n- 1x Ankara Dress (Size M) — Ksh 2500.00\n\nTotal: Ksh 2500.00\n\nReply 'checkout' to complete your order, or send another product name/number to add more.	2026-07-15 22:27:33.516086+03	en	\N
322	9	5	customer	checkout	2026-07-15 22:29:13.056975+03	en	\N
323	9	5	assistant	Almost done! Please share your name and contact number.	2026-07-15 22:29:13.542671+03	en	\N
324	9	5	customer	checkout	2026-07-15 22:33:20.280005+03	en	\N
325	9	5	assistant	Thank you, checkout! Your order has been placed ✅\nOrder reference: #766da280\n\n- 1x Ankara Dress — Ksh 2500.00 — _pending_\n\nTotal: Ksh 2500.00\n\nWe'll contact you at +254706040948 to confirm payment & delivery.\n\n_Each item is tracked separately, so status may update at different times._	2026-07-15 22:33:21.009078+03	en	\N
326	9	5	customer	Factor	2026-07-16 14:07:36.560674+03	en	\N
327	9	5	assistant	Welcome to Factor! Here's what we have in Dress: Ankara Dress, chiffon dress 👇\n\nReply with a product name to see more and order.\n\n_Tip: reply 'menu' anytime to browse other stores._	2026-07-16 14:07:37.040765+03	en	\N
328	9	5	customer	Ankara dress	2026-07-16 14:08:03.7968+03	en	\N
329	9	5	assistant	Great choice! *Ankara Dress* — Ksh 2500.00\nSIze: S,M,L,XL,XXL\n\nWhich one would you like?	2026-07-16 14:08:04.284662+03	en	\N
330	9	5	customer	m	2026-07-16 14:08:18.888125+03	en	\N
331	9	5	assistant	How many would you like?	2026-07-16 14:08:19.376479+03	en	\N
332	9	5	customer	2	2026-07-16 14:08:29.580047+03	en	\N
333	9	5	assistant	Added: 2x Ankara Dress — Ksh 5000.00\n\nYour cart:\n- 2x Ankara Dress (Size M) — Ksh 5000.00\n\nTotal: Ksh 5000.00\n\nReply 'checkout' to complete your order, or send another product name/number to add more.	2026-07-16 14:08:30.071522+03	en	\N
334	9	5	customer	checkout	2026-07-16 14:08:52.150983+03	en	\N
335	9	5	assistant	Almost done! Please share your name and contact number.	2026-07-16 14:08:52.628564+03	en	\N
336	9	5	customer	liv 0157821409	2026-07-16 14:09:17.504329+03	en	\N
337	9	5	customer	liv 0157821409	2026-07-16 14:19:27.980907+03	en	\N
338	9	5	assistant	Thank you, liv! Your order has been placed ✅\nOrder reference: #173b7354\n\n- 2x Ankara Dress — Ksh 5000.00 — _pending_\n\nTotal: Ksh 5000.00\n\nWe'll contact you at 0157821409 to confirm payment & delivery.\n\n_Each item is tracked separately, so status may update at different times._	2026-07-16 14:19:28.525895+03	en	\N
339	7	1	customer	Zawadi Boutique	2026-07-16 15:49:01.12156+03	en	\N
340	7	1	assistant	Welcome to Zawadi Boutique! Here's what we have in Jeans: Wide legged trousers 👇\n\nReply with a product name to see more and order.\n\n_Tip: reply 'menu' anytime to browse other stores._	2026-07-16 15:49:01.661174+03	en	\N
341	7	1	customer	where do you guys deliver	2026-07-16 15:51:32.682705+03	en	\N
342	7	1	customer	where do you guys deliver	2026-07-16 15:51:33.178415+03	en	\N
343	7	1	assistant	We deliver to various locations. Could you please specify which area you're interested in? That way, I can confirm if we deliver to your location.	2026-07-16 15:51:33.649259+03	en	\N
344	7	1	customer	hey	2026-07-16 16:38:00.399787+03	en	\N
345	7	1	customer	hey	2026-07-16 16:38:01.264561+03	en	\N
346	7	1	assistant	Hello! Welcome to Zawadi Boutique. How can I help you today?	2026-07-16 16:38:01.764068+03	en	\N
347	9	5	customer	Factor	2026-07-16 16:43:33.712031+03	en	\N
348	9	5	assistant	Welcome to Factor! Here's what we have in Dresses: chiffon dress, Ankara Dress 👇\n\nReply with a product name to see more and order.\n\n_Tip: reply 'menu' anytime to browse other stores._	2026-07-16 16:43:34.208281+03	en	\N
349	9	5	customer	chiffon dress	2026-07-16 16:44:16.258254+03	en	\N
350	9	5	assistant	Great choice! *chiffon dress* — Ksh 2000.00\nsize: s, m, l, xxl\n\nWhich one would you like?	2026-07-16 16:44:17.180476+03	en	\N
351	9	5	customer	m	2026-07-16 16:44:37.134233+03	en	\N
352	9	5	assistant	How many would you like?	2026-07-16 16:44:37.647649+03	en	\N
353	9	5	customer	1	2026-07-16 16:44:47.689059+03	en	\N
354	9	5	assistant	Added: 1x chiffon dress — Ksh 2000.00\n\nYour cart:\n- 1x chiffon dress (Size m) — Ksh 2000.00\n\nTotal: Ksh 2000.00\n\nReply 'checkout' to complete your order, or send another product name/number to add more.	2026-07-16 16:44:48.246709+03	en	\N
355	9	5	customer	checkout	2026-07-16 16:45:55.470056+03	en	\N
356	9	5	assistant	Almost done! Please share your name and contact number.	2026-07-16 16:45:55.996108+03	en	\N
357	9	5	customer	anne 0765312687	2026-07-16 16:46:19.408995+03	en	\N
358	9	5	assistant	Thank you, anne! Your order has been placed ✅\nOrder reference: #2cb6ea39\n\n- 1x chiffon dress — Ksh 2000.00 — _pending_\n\nTotal: Ksh 2000.00\n\nWe'll contact you at 0765312687 to confirm payment & delivery.\n\n_Each item is tracked separately, so status may update at different times._	2026-07-16 16:46:19.967264+03	en	\N
359	9	5	customer	Factor	2026-07-16 16:50:24.449587+03	en	\N
360	9	5	assistant	Welcome to Factor! Here's what we have in Handbags: Prada Handbag 👇\n\nReply with a product name to see more and order.\n\n_Tip: reply 'menu' anytime to browse other stores._	2026-07-16 16:50:24.964452+03	en	\N
361	9	5	customer	gucci handbag	2026-07-16 16:50:53.062571+03	en	\N
362	9	5	customer	gucci handbag	2026-07-16 16:50:53.581041+03	en	\N
363	9	5	assistant	Let me connect you with our team for that.	2026-07-16 16:50:54.06479+03	en	\N
364	9	5	human	we currently don't have that	2026-07-16 16:52:13.493944+03	en	delivered
\.


ALTER TABLE public.conversations ENABLE TRIGGER ALL;

--
-- Data for Name: products; Type: TABLE DATA; Schema: public; Owner: postgres
--

ALTER TABLE public.products DISABLE TRIGGER ALL;

COPY public.products (id, user_id, name, description, price, is_available, created_at, updated_at, variant_label, variant_options, unit, image_url, upsell_text, category_id) FROM stdin;
7	1	Test Product	test desc	1000.00	f	2026-06-20 15:07:50.937375+03	2026-06-26 14:00:33.473044+03	\N	\N	\N	\N	\N	\N
11	1	Zara Ladies Heels	Zara open 6-inch high heels with a pointed tip	3000.00	t	2026-06-23 11:04:05.879505+03	2026-06-23 11:34:27.351265+03	Size 38, black	\N	per pair	/uploads/products/1/11_ 499c3ec0.jpeg	Pair this with a mini  black zara handbag.Retailing at 2500	1
9	1	Wide legged trousers	Cotton fabric jeans	2500.00	t	2026-06-23 06:50:41.053738+03	2026-06-23 10:51:25.2557+03	levi's	Large	\N	/uploads/products/1/9_ 7c85e4e4.jpg	\N	2
8	1	Pashmina shawl	Wooven Pakistan shawl scarf	1500.00	t	2026-06-22 15:34:39.035422+03	2026-06-23 07:41:46.112186+03	Medium	Red	per piece	\N	\N	3
10	1	Silk Skirt	Silk made skirt	1500.00	t	2026-06-23 10:54:37.94685+03	2026-06-24 12:44:28.905829+03	Size	S,M,L,XL	per piece	/uploads/products/1/10_ c741cddf.jpg	Pair this with a white tank top retailing at 1000	4
6	1	Ankara Dress	Hand-stitched ankara fabric dress, sizes L-XL	3200.00	t	2026-06-17 12:40:30.850824+03	2026-06-22 13:56:31.58681+03	size 10	African themed orange	\N	\N	\N	5
14	5	chiffon dress	Indian material chifon	2000.00	t	2026-07-10 14:15:02.669315+03	2026-07-16 14:43:09.408487+03	size	s, m, l, xxl	per piece	/uploads/products/5/14_57d61905.jpeg	\N	7
13	5	Ankara Dress	\N	2500.00	t	2026-07-08 14:26:55.574004+03	2026-07-16 14:43:31.482685+03	SIze	S,M,L,XL,XXL	per piece	/uploads/products/5/13_2279911d.jpeg	\N	7
15	5	Silk Shawl	It is a 1.5m white silk scarf with cotton thread stitchings	600.00	t	2026-07-16 14:45:55.5923+03	2026-07-16 14:45:55.890583+03	label	White, pink, red, cream	per piece	/uploads/products/5/15_5db2c967.jpeg	\N	6
16	5	Boho Skirt	A green-cotton material boho skirt	1500.00	t	2026-07-16 14:48:08.719012+03	2026-07-16 14:48:09.014308+03	Size	S, L,XL, XXL	per piece	/uploads/products/5/16_99eedb14.jpeg	\N	8
17	5	Lacy Skirt	Lace material ,brown cheetah print skirt	2000.00	t	2026-07-16 14:50:39.313393+03	2026-07-16 14:50:39.583577+03	Size	m, xl,l	per piece	/uploads/products/5/17_f3368098.jpeg	\N	8
18	5	Prada Handbag	Brown leather handbag hand-stitched bag with gold details	2200.00	t	2026-07-16 14:53:36.914717+03	2026-07-16 14:53:37.174285+03	Color	Burgundy,red,black ,brown	per piece	/uploads/products/5/18_2ec111b7.jpeg	\N	9
19	5	Jeans shorts	Blue washed mid thigh shorts for women	1500.00	t	2026-07-16 14:58:17.743571+03	2026-07-16 14:58:18.046374+03	Size	S, M,L,XL	per piece	/uploads/products/5/19_773fd564.jpeg	\N	10
\.


ALTER TABLE public.products ENABLE TRIGGER ALL;

--
-- Data for Name: marketplace_sessions; Type: TABLE DATA; Schema: public; Owner: postgres
--

ALTER TABLE public.marketplace_sessions DISABLE TRIGGER ALL;

COPY public.marketplace_sessions (id, phone_number, pending_action, selected_business_type, selected_business_id, updated_at, selected_product_id, selected_size, list_offset) FROM stdin;
1	+254706040948	awaiting_product_choice	Handbags	5	2026-07-16 16:50:24.407605+03	\N	\N	0
\.


ALTER TABLE public.marketplace_sessions ENABLE TRIGGER ALL;

--
-- Data for Name: orders; Type: TABLE DATA; Schema: public; Owner: postgres
--

ALTER TABLE public.orders DISABLE TRIGGER ALL;

COPY public.orders (id, customer_id, product_id, user_id, quantity, total_amount, status, created_at, updated_at, snapshot_customer_name, snapshot_customer_phone, snapshot_product_name, snapshot_product_price, snapshot_business_name, order_group_id) FROM stdin;
1	9	14	5	2	4000.00	pending	2026-07-13 13:45:41.244398+03	\N	Jane	0712568360	chiffon dress	2000.00	Factor	\N
2	9	13	5	2	5000.00	pending	2026-07-15 14:21:34.584079+03	\N	John	0785611145	Ankara Dress	2500.00	Factor	a4f2f57c-1ce1-4018-8c58-cc50a4731405
3	9	13	5	1	2500.00	pending	2026-07-15 22:33:20.838727+03	\N	checkout	+254706040948	Ankara Dress	2500.00	Factor	766da280-12e0-438d-b67b-2ad324a7da2e
4	9	13	5	2	5000.00	pending	2026-07-16 14:19:28.469903+03	\N	liv	0157821409	Ankara Dress	2500.00	Factor	173b7354-790c-4087-8a4f-b4dbe4124e25
5	9	14	5	1	2000.00	pending	2026-07-16 16:46:19.923551+03	\N	anne	0765312687	chiffon dress	2000.00	Factor	2cb6ea39-39a4-4967-a667-b059756fbf4e
\.


ALTER TABLE public.orders ENABLE TRIGGER ALL;

--
-- Name: carts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.carts_id_seq', 2, true);


--
-- Name: categories_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.categories_id_seq', 10, true);


--
-- Name: conversation_states_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.conversation_states_id_seq', 7, true);


--
-- Name: conversations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.conversations_id_seq', 364, true);


--
-- Name: customers_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.customers_id_seq', 9, true);


--
-- Name: marketplace_sessions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.marketplace_sessions_id_seq', 1, true);


--
-- Name: orders_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.orders_id_seq', 5, true);


--
-- Name: products_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.products_id_seq', 19, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.users_id_seq', 6, true);


--
-- PostgreSQL database dump complete
--

\unrestrict pkskYHyivyU1vyw4bm21i6fs8b7Rh6eMY9Fv3VkWYbuJ9Vs078Ko5ouMWdExvak

