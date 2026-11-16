# Q&A defence — answers that match what the system shows

The plan's scripted answers (§6.4), rewritten where our results differ, plus the questions our extra work invites.
Every number below is in `notebooks/03_layer4_decision.ipynb` (last table) or on the website. About 20 seconds each.

## The plan's nine questions

**1. Why is your training data from 2006–2015?**
The USAID shipment history (7,771 shipments to learn from, 2,545 later ones to test on) only teaches the model how
shipping behaves: air versus sea, origin, delivery terms, freight share. The suppliers we rank are today's 18 carboplatin
labelers from the FDA. In a pilot the model would retrain monthly on the buyer's own delivery data; we describe that, we
did not build it.

**2. Doesn't low vendor overlap flatten your ML score?** *(plan answer changed)*
Partly, and we show it openly. The model scores each supplier by its factory's country, so in the real data there are 4
different late-delivery scores, not 11: all Indian factories score the same, because the shipping details of UAE orders
are not public. In the synthetic view, where each supplier gets its own shipping terms and delivery record, all 11
scores differ. We chose not to invent the missing details in the real view.

**3. Why combine AHP-TOPSIS with ML instead of ML alone?**
ML predicts what is likely to happen; it cannot know how much the board cares about cost versus safety for a
life-critical drug. The board's weights (cost 10%, late delivery 30%, billing 5%, compliance 30%, route 25%) turn the
predictions into a ranking, and the solver turns the ranking into an exact order split.

**4. In a Hormuz crisis, who has time for an AHP survey?** *(plan answer changed)*
Nobody: the weights are set once per tier, and Crisis is one click. It moves 10% of the weight from cost to route
exposure and stresses every route by 1.5 times. In the real data the ranking changes (6 of 11 suppliers move; Avyxa goes
from 6th to 1st), but the order stays 30/30/30/10, because Avyxa costs about 84 times more ($2,355 against $28 a vial)
and the split still weighs price. In the synthetic view Crisis also changes the order: Teva replaces Hospira as the main
supplier.

**5. Won't a brand-new supplier always rank last?** *(plan answer changed)*
No. Missing history is treated as neutral, not bad. A new supplier is scored on its FDA record and route like everyone
else, and if the solver picks it, it gets at least 5% and at most 15% (30% when fewer than two suppliers are established),
the plan's §4.4 rules. It is not forced into every order: that would override the ranking.

**6. Isn't using US FDA data for a UAE buyer a stretch?**
The FDA inspects the factories that supply the Gulf (India, Europe, Australia); a serious finding or a sterility letter is a
quality signal wherever the vials go. The UAE regulator (EDE) publishes no inspection results, warning letters or shortage
list, so the FDA record is the best public evidence. One thing a buyer must still check: in the EDE's public register
(16 Nov 2026) none of our 11 suppliers has carboplatin registered in the UAE yet, so an order would need registration or a
special import permit.

**7. What if the AI makes a wrong prediction?**
It never orders anything. A category manager sees the top three reasons behind each delivery score and approves, overrides
or rejects; every decision is fingerprinted in a log that shows any later edit. The model catches 92% of late shipments
it has never seen, so some false alarms are the price of not missing delays.

**8. How do you handle UAE data privacy and fairness?**
No personal data in the scores; approvers sign with initials only; names and e-mails in letters and contracts are removed
(UAE PDPL, Decree-Law 45 of 2021). Each supplier is judged on its own factory's record, never on its country's name or its
parent company's record.

**9. What is the ROI of the 90-day pilot?**
Four KPIs: time to switch supplier (25 days today) toward an approved warm backup; dual sourcing on every Tier 1 drug
(today's split uses 4 factories in 3 countries, with a warm-backup share of 70%); on-time-in-full delivery; and zero
stock-outs. The stress test shows the value: if every Indian factory stopped, the order would still be covered.

## Questions our extra work invites

**Why 30/30/30/10 and not the plan's 70/20/10?**
The plan's caps are limits, not targets. No supplier has a delivery record of its own with the buyer, so the plan caps
each factory at 30%; four factories are needed. With a synthetic delivery record for the five biggest US sellers, the split
becomes 37/33/15/15.

**What does the stress test show?**
Losing any one factory changes nothing. Losing all 4 Indian factories keeps the order covered, but Avyxa has to supply
1,000 vials and the monthly cost rises from $279,546 to $2,607,054 at official US prices. If Fresenius's unstated factory
is also in India, 1,000 vials must be bought in an emergency ($7,234,115 a month).

**What does the risk dial do, and why does moving it change nothing?**
It sets how much the order split pays for safety (0 = ignore risk, higher = prefer higher-ranked suppliers). It does not
change the ranking. In our data the ten generic suppliers all cost the same ($28 a vial), so any positive setting prefers
them in the same order and the 30%-per-factory share limits decide the split: the split at 0 differs from the split at
0.25, and every setting from 0.25 to 3 gives the same result. The dial would matter once suppliers quote different
prices, which real tender quotes would give.

**Isn't synthetic data just made up?**
Yes, and it is labelled as such. Every invented value comes from a stated range with a source (air-freight indices,
invoice-error benchmarks, USAID on-time rates, real US market shares), is drawn once with a fixed seed, and is marked on
screen. No model is trained on it; the late-delivery model's test score is unchanged. The real view never uses it.

**Billing oddities has no data: why keep it?**
In the real data no supplier has its own invoices, so the mark is the same for all and has no effect (removing its 5% weight
changes nothing). The model is ready for real invoices; on synthetic invoices it found all 8 planted errors.

**Why a website as well as Streamlit?**
Streamlit is the operator tool the plan asks for (four tabs plus the data pipeline, with approve-and-log). The website lets
anyone explore the same results without installing anything; both show the same numbers, checked automatically.
