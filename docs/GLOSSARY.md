# PharmaShield GCC — Plain-English Glossary

Every piece of jargon used in the Master Implementation Plan, the code and the team's discussions, one plain line each.
Terms are grouped by topic. Numbers quoted (for example model scores) are from the 15 November 2026 run.

**Two words mean two different things in this project. Check which one is meant.**

| Word | Meaning 1 | Meaning 2 |
|---|---|---|
| **API** | In pharma: *Active Pharmaceutical Ingredient*, the raw drug powder. | In software: *Application Programming Interface*, a way for our code to fetch data from a website (for example "the openFDA API"). |
| **Label** | In pharma: the official printed information for a drug (on DailyMed). | In AI: the correct answer attached to a training example (for example "this shipment was late"). |

---

## 1. Shipping and trade

**Incoterms** are standard codes for who handles the shipping, the seller or the buyer.

| Term | Plain meaning |
|---|---|
| **EXW** (Ex Works) | The buyer collects from the factory gate. The buyer arranges all transport. |
| **FCA** (Free Carrier) | The seller hands the goods to the buyer's transport company. |
| **CIP** (Carriage and Insurance Paid) | The seller pays freight and insurance to the destination. |
| **CIF** (Cost, Insurance, Freight) | The sea-freight version of the same idea. |
| **DAP** (Delivered At Place) | The seller delivers to the destination. The buyer handles import taxes. |
| **DDU** | The older name for DAP. |
| **DDP** (Delivered Duty Paid) | The seller does everything, including import taxes. It arrives at your door. |
| **RDC** | Not an Incoterm. In the SCMS data it means "shipped from the aid agency's own regional warehouse". |

Why this matters to us: Layer 1 assumes every carboplatin supplier ships DDP. In the old data, DDP shipments were
late more often than EXW ones (13% vs 5%), so that assumption alone moves the late-delivery mark (C2).

| Term | Plain meaning |
|---|---|
| **Freight** | The cost of transporting the goods. |
| **Insurance** | The cost of insuring the goods during transport. |
| **Landed cost** | The total cost to get one vial to you: price + freight + insurance. C1 is based on it (freight to the UAE has no data, so it is left out). |
| **Freight-to-value ratio** | Freight cost divided by goods value. A $4,000 freight bill on $5 of goods is suspicious. |
| **Shipment mode** | Air, sea (ocean) or truck. |
| **Air charter** | A whole aircraft hired for one shipment. |
| **Corridor / lane** | The route goods travel, for example India to Dubai by sea. |
| **Strait of Hormuz** | The narrow sea passage into the Gulf. Ships to Dubai's main port must pass through it. |
| **Gulf airspace** | The sky over the Gulf region. Flights into the UAE can be rerouted or suspended when it closes. |
| **Chokepoint** | A narrow route with no easy alternative. |
| **Jebel Ali / Khor Fakkan / Fujairah** | UAE ports. Jebel Ali is inside Hormuz. The other two are outside, so they are safer. |
| **Free zone / bonded warehouse** | A storage area where imported goods can sit before import taxes are paid. |
| **War-risk surcharge** | An extra shipping fee charged when a route becomes dangerous. |
| **Cold chain** | Keeping a drug refrigerated for the whole journey. |
| **LPI** (Logistics Performance Index) | A World Bank score from 1 to 5 for how good a country's shipping and customs are. |
| **WGI** (Worldwide Governance Indicators) | A World Bank score for how politically stable a country is. |

## 2. Medicines and the drug regulator

| Term | Plain meaning |
|---|---|
| **Carboplatin** | A chemotherapy (cancer) drug. It is our demo product. |
| **Molecule** | The drug substance itself (carboplatin), regardless of brand or maker. |
| **Oncology** | Cancer medicine. |
| **ARV** (antiretroviral) | HIV medicines. Our old shipment data is mostly these. |
| **HRDT** | HIV rapid test kits. The second-largest product group in the old shipment data. |
| **Injectable / vial** | A drug given by needle, and the small glass bottle it comes in. |
| **Multi-dose vial** | A vial that holds several doses. |
| **Dosage form** | The physical form of a drug: tablet, injection, cream. |
| **Strength / concentration** | How much drug is in each unit. Ours is 10 mg per mL. |
| **Sterile** | Completely germ-free. This is critical for injections, so sterility failures are the most serious. |
| **Aseptic / media fill** | Germ-free manufacturing, and the practice run a factory does to prove it works. |
| **Particulate / endotoxin** | Tiny particles, or bacterial residue, found in a product. Common reasons for recalls. |
| **Generic** | A copy of a drug sold by many companies once the patent has expired. |
| **API / bulk powder** | The raw active ingredient before it becomes a finished vial. 7 of our 18 companies sell only this, so we do not rank them. |
| **Finished injection** | The ready-to-use vial. Only the 11 companies that sell this are ranked. |
| **SKU** | One specific product, for us "Carboplatin Injection 10 mg/mL". |
| **FDA** | The US government's drug regulator. |
| **openFDA** | The FDA's free public database. |
| **NDC** (National Drug Code) | The US ID number for a drug product. The NDC Directory lists who is allowed to sell what. |
| **Labeler** | The company whose name is on the box. It is not always the company that makes the drug (Apotex's carboplatin is made by Teyro Labs). |
| **Contract manufacturer** | A factory that makes a drug for another company to sell under its own name. |
| **Repackager** | A company that only re-boxes someone else's product. Excluded from our list. |
| **Marketing authorisation** | Legal permission to sell a drug. |
| **Establishment** | A factory or lab registered with the FDA for a specific job (manufacture, testing, labelling). |
| **DailyMed / SPL** | The website holding official drug labels, and the label file format. |
| **ANDA / 505(b)(2)** | Two types of US approval. ANDA is for a generic copy. 505(b)(2) is for a modified version, such as Avyxa's branded Kyxata, which is why it is expensive. |
| **Kyxata** | Avyxa's brand name for its carboplatin. |
| **CGMP** | "Current good manufacturing practice", the factory quality rules. |
| **Inspection** | The FDA visits a factory to check it. |
| **NAI / VAI / OAI** | Inspection results: all fine / minor issues / serious problems. OAI is the red flag. |
| **FEI** | The FDA's ID number for one factory. |
| **Form 483** | The list of problems inspectors hand over at the end of a visit. |
| **Warning letter** | A formal public FDA letter saying a factory has serious problems. |
| **Import alert** | An FDA order that stops a factory's products at the US border. |
| **Data integrity** | Whether factory records are honest and complete (not deleted or backdated). |
| **Process validation** | Proof that the manufacturing process gives the same result every time. |
| **Quality unit** | The factory's internal quality-control team. |
| **21 CFR 211** | The US rulebook for drug factories. Warning letters cite sections of it. |
| **ICH Q7** | The equivalent rulebook for factories that make raw ingredients (APIs). |
| **Bioresearch monitoring** | FDA inspections of clinical-trial sites, not factories. We exclude them. |
| **Recall, Class I / II / III** | A product pulled from the market. Class I is the most dangerous and Class III the least. |
| **Drug shortage** | The FDA's list of drugs in short supply. |
| **WHO Essential Medicines List** | The World Health Organization's list of must-have drugs. |
| **CMS / ASP / HCPCS / J-code** | The US Medicare price list, its "average sales price", and the billing codes (carboplatin is J9045). We use these as our price stand-in. |
| **Reimbursement benchmark** | The price an insurer pays for a drug. A public stand-in for a real supplier quote. |

## 3. Buying, contracts and the business case

| Term | Plain meaning |
|---|---|
| **GPO** (Group Purchasing Organisation) | One body that buys for many hospitals. It is our customer. |
| **Category manager** | The buyer responsible for one group of products. The daily user of our tool. |
| **C-suite (CPO, CFO, COO)** | The top executives: heads of procurement, finance and operations. They decide on the pilot. |
| **Tender** | A formal bidding process to pick a supplier. |
| **Quote** | The price a supplier offers. |
| **ERP** | A company's internal system for orders and deliveries. |
| **Purchase order (PO)** | One formal order placed with a supplier. |
| **Invoice line / line item** | One row on a bill: one product, one quantity, one price. |
| **Tatmeen / GS1** | The UAE's system for tracking every medicine pack by barcode, and the barcode standard. |
| **Serialisation** | Giving every single pack its own unique code. |
| **MoHAP** | The UAE Ministry of Health and Prevention. |
| **Rafed (PureHealth)** | A large UAE healthcare purchasing organisation. The plan uses it as the model for our customer. |
| **MSA** | Master Supply (or Service) Agreement: the main contract with a supplier. |
| **Clause** | One numbered rule inside a contract. |
| **Force majeure** | The "not our fault" clause. It lets the supplier off for events like war. The risk is a supplier listing a Hormuz closure there. |
| **Lead time** | The number of days from order to delivery. |
| **Liquidated damages** | A pre-agreed fine for late delivery. |
| **Sole / single source** | Buying from only one supplier. |
| **Exclusivity** | A contract rule that stops the buyer using a second supplier. |
| **Dual sourcing** | Splitting orders across two or more suppliers, so one failure does not stop supply. |
| **Warm backup** | A second supplier that is already approved and receiving small orders, so it can scale up quickly. |
| **Safety stock / consignment stock** | Extra inventory kept as a cushion, sometimes owned by the supplier but stored near the buyer. |
| **Strategic stockpile** | A national emergency reserve of medicines. |
| **Pro-rata allocation** | In a shortage, each customer gets a share in proportion to its past orders. |
| **Capacity** | The most a supplier can make per month. |
| **Demand** | How much the buyer needs. Ours is 10,000 vials per month. |
| **Stock-out** | Running out of a product completely. |
| **Spot buy** | An emergency purchase outside the contract, usually at a high price. |
| **OTIF** | "On time, in full": the share of orders that arrive complete and on time. |
| **Probation** | Our label for a supplier with fewer than 5 past deliveries on record. It gets a small trial order. |
| **Criticality tier** | How life-critical a drug is. Tier 1 is life-critical, like carboplatin. |
| **Pilot** | A small trial run of a new system (ours is 90 days) before full rollout. |
| **KPI** | Key performance indicator: a number used to judge success. |
| **ROI** | Return on investment: what you gain compared with what you spend. |
| **Working capital** | Money tied up in stock and unpaid bills. Dual sourcing can raise it. |

## 4. Our datasets

| Term | Plain meaning |
|---|---|
| **SCMS** | The old US aid programme's record of about 10,000 medicine shipments (2006–2015). It is our "teacher" data. |
| **USAID** | The US aid agency that ran it. |
| **GHSC-PSM** | A newer version of the same kind of data. It is optional and we skipped it. |
| **Proxy** | A stand-in used when the real data is secret or missing. |
| **Scenario assumption** | A number the team chose because no real one exists. It must be labelled as such. |
| **Synthetic** | Made up for testing. Our 11 supplier contracts are synthetic. |
| **Panel** | The list of manufacturers we score (18 in total, 11 rankable). |
| **Suppliers matrix** | The final table: one row per manufacturer, with all five marks. |

## 5. Data and software terms

| Term | Plain meaning |
|---|---|
| **Pipeline** | A series of steps that turn raw data into the final table. |
| **Ingestion** | Fetching data and loading it into our system. |
| **Live API call** | Our code asking a website for today's data. |
| **Cache / offline replay** | A saved copy of what a website returned, so the run can be repeated without the internet. |
| **Snapshot** | A frozen copy of the data at one moment. |
| **CSV** | A simple table file that opens in Excel. |
| **JSON** | A text format for structured data. |
| **Schema / locked schema** | The agreed list of columns in a table. "Locked" means nobody changes it. |
| **Normalise** | Squash numbers onto a 0-to-1 scale so they can be compared. |
| **Min-max** | One way to normalise: the lowest becomes 0 and the highest becomes 1. It can stretch tiny gaps. |
| **Impute** | Fill in a missing value with a reasonable guess. |
| **Median** | The middle value when the numbers are sorted. |
| **Percentile (p90)** | The value that 90% of the numbers fall below. |
| **Outlier / anomaly** | A value far from normal. |
| **Quarantine** | Set bad rows aside with a reason, not silently delete them. |
| **Deduplicate** | Remove repeated rows. |
| **Coerce** | Force text into a number or date, turning unreadable values into blanks. |
| **Look-back window** | How far into the past we count. Ours is 5 years for inspections and recalls. |
| **Entity resolution** | Working out that "Hospira Inc" and "HOSPIRA, INC., a Pfizer Company" are the same company. |
| **rapidfuzz / fuzzy match** | A tool that scores how similar two names are (0–100). |
| **Alias / parent company** | Another name for a company, or its owner (Eugia is owned by Aurobindo). |
| **PII / redaction** | Personal details such as names, emails and phone numbers, and blacking them out. |
| **Hash (SHA-256)** | A fingerprint of a file. If the file changes, the fingerprint changes. |
| **Repository (repo) / commit / push** | The shared project folder on GitHub, saving a set of changes, and uploading them. |
| **.gitignore** | A list of files that are deliberately not uploaded. |
| **Virtual environment (venv)** | A private install of Python tools for one project. |
| **Notebook** | A document that mixes code and its results, run from top to bottom. |
| **Streamlit** | The tool that turns our Python code into a web page (the cockpit). |
| **Test (unit test)** | A small automatic check that a piece of code does what it should. |

## 6. AI and model terms

| Term | Plain meaning |
|---|---|
| **Model** | A program that learns patterns from past examples to make predictions. |
| **Feature** | One input the model looks at (country, shipping mode and so on). |
| **Target** | The thing the model tries to predict. Ours is "was the shipment late?" |
| **Train / test split** | Teach on one part of the data, then examine on another part the model never saw. |
| **Validation set** | A third slice used for choosing settings, so the test stays untouched. |
| **Out-of-time test** | The exam uses later years than the teaching, which is like predicting the future. |
| **Leakage** | The model accidentally sees the answers while learning. A form of cheating. |
| **Overfitting** | The model memorises the teaching data and then does badly on new data. |
| **Cross-validation / out-of-fold** | Splitting the data into parts and taking turns, so every example is scored by a model that never saw it. |
| **Hyperparameter / tuning** | A setting of the model, and trying several to pick the best. |
| **Random seed (random_state)** | A fixed starting number so the result is identical every run. |
| **XGBoost** | A popular prediction method built from many small decision trees. It produces our C2. |
| **Logistic regression** | A simple, classic prediction method. |
| **Baseline** | The simple method you must beat to justify the fancy one. |
| **Probability / predict_proba** | The model's answer as a chance between 0 and 1. |
| **Inference** | Using a trained model to score new cases. |
| **Feature-based inference** | Scoring a supplier from its characteristics (country, mode) instead of its own history. |
| **Threshold** | The cut-off above which we call something "late". |
| **ROC-AUC** | An overall score for a predictor. 0.5 is coin-flipping and 1.0 is perfect. Ours is 0.80. |
| **Recall** | Of the truly late shipments, the share we caught (92%). |
| **Precision** | Of the ones we flagged, the share that really were late (20%). |
| **False alarm (false positive)** | Flagged as late but arrived on time. |
| **Miss (false negative)** | Not flagged but arrived late. |
| **F1 / F2** | Single numbers that combine recall and precision. F2 counts recall more. |
| **Confusion matrix** | A 2×2 table of right and wrong predictions. |
| **Class imbalance / scale_pos_weight** | Only 11% of shipments are late, so the model would ignore them. This setting makes it pay more attention to late ones. |
| **Base rate** | How often something happens overall (11% late). |
| **Site prior** | A factory's past late rate, used as an input. |
| **Smoothing** | Pulling a rate based on very few shipments towards the overall average. |
| **Distribution shift** | The new cases differ from the teaching data (oncology vials vs HIV pills). |
| **SHAP** | A method that explains why a model gave a score: "these 3 things pushed it up". |
| **Feature importance** | Which inputs the model relies on most overall. |
| **Explainability** | Being able to show a human why the model said what it said. |
| **Isolation Forest** | A method that finds unusual rows. It produces our C3. |
| **Contamination = 0.05** | A setting telling it to flag the oddest 5%. |
| **Unsupervised** | Learning without correct answers. Isolation Forest is unsupervised. |
| **NLP** | Getting computers to read text. |
| **TF-IDF** | Turning text into numbers by counting the important words. |
| **Classifier** | A model that sorts things into categories. |
| **Weak labels** | Answers produced by a rule instead of a human. Ours come from which regulations a letter cites. |
| **LLM** | A large AI language model, such as Claude. |
| **Zero-shot** | Asking an LLM to do a task with no training examples. |
| **Retraining** | Teaching the model again on newer data. The plan says monthly. |

## 7. Ranking and decision terms

| Term | Plain meaning |
|---|---|
| **C1–C5 (criteria)** | The five marks: cost, late delivery, billing oddities, compliance, route risk. Each runs from 0 (best) to 1 (worst). |
| **MCDM** | Multi-criteria decision-making: choosing when several things matter at once. |
| **Decision matrix** | The table of suppliers (rows) against the five marks (columns). |
| **Weights** | How much each mark counts towards the final rank. They add up to 1. |
| **AHP** (Analytic Hierarchy Process) | A method that turns the bosses' opinions ("delivery matters more than cost") into weights. |
| **Pairwise comparison** | Comparing the marks two at a time. This is how AHP collects opinions. |
| **Consistency ratio (CR)** | A check that those opinions do not contradict each other. It must be below 0.10. |
| **Entropy weights** | Weights worked out from the data itself: a mark that varies more counts more. |
| **Hybrid weights** | The plan's mix: half AHP (opinion) plus half entropy (data). This prototype uses the board's AHP weights by default, with entropy on a slider (it proved unstable on 11 suppliers). |
| **TOPSIS** | The formula that combines the five marks into one rank, by closeness to an ideal supplier. |
| **Ideal best / ideal worst** | An imaginary supplier with the best (or worst) value on every mark. |
| **Closeness score (S)** | TOPSIS's result, from 0 to 1. Higher is better. |
| **Linear programming (LP) / PuLP** | Maths that finds the best order split under rules, and the Python tool that does it. |
| **Decision variable** | A number the maths is free to choose. Ours is how many vials each supplier gets. |
| **Objective** | What the maths tries to minimise. Ours is cost plus a penalty for risky suppliers. |
| **Constraint** | A rule the split must obey, such as "max 70% to one supplier". |
| **Feasible / infeasible** | Whether any split exists that obeys all the rules. |
| **Slack variable** | A safety valve. Ours is the emergency spot buy, so the maths always has an answer. |
| **Penalty M (big-M)** | A huge made-up cost on the spot buy, so it is used only as a last resort. |
| **Lambda (λ)** | A dial that sets how much the split cares about risk compared with cost. |
| **Binary variable** | A yes-or-no choice inside the maths, such as "is this supplier used at all?" |
| **Concentration cap** | The maximum share one supplier may get. |
| **70/20/10** | The plan's example split: main supplier, backup, trial supplier. It needs a supplier with its own delivery record; while all suppliers are new, the plan's rules cap each factory at 30%. |
| **Normal / Crisis / Cost Focus mode** | Three preset weight settings. Crisis shifts weight from cost to route risk. |
| **Stress factor** | In Crisis mode, route risk is multiplied by 1.5. |
| **Stress test / scenario** | Asking "what if this bad thing happens?" and re-running the numbers. Here: a natural disaster takes factories offline and the order split re-solves. |
| **Sensitivity analysis** | Changing one input to see how much the answer moves. |

## 8. Governance and compliance

| Term | Plain meaning |
|---|---|
| **Human-in-the-loop** | A person must approve every recommendation. |
| **Audit log / audit trail** | A permanent record of who approved what and when. |
| **Immutable** | Cannot be edited afterwards. |
| **PDPL** | The UAE's personal-data privacy law (Federal Decree-Law 45 of 2021). |
| **Data minimisation / purpose limitation** | Collect only the personal data you need, and use it only for the stated reason. |
| **UAE AI Charter** | The UAE's 2024 principles for AI: transparency, human oversight, safety. |
| **Algorithmic fairness** | The system must not treat suppliers unfairly, for example by country alone. |
| **GenAI disclosure** | Marking anything an AI wrote. Ours uses a red dashed outline plus a prompt log. |
| **Prompt log** | The record of what the team asked the AI to do. |
