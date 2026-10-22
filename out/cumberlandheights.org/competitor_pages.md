# Competitor page comparison

Pages that win Nashville rehab SERPs vs the audited site's money pages (single fetch each, raw HTML, no JS rendering).

| Page | Title len | Svc+Geo title | H1s | Words | H2s | FAQ | Schema types | Tel (hdr) | Forms | Insurers | 24/7 | Accred. | Verify ins. | Review hints | Img alt |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| apex.rehab/tennessee/nashville | 49 | yes | 1 | 7239 | 18 | yes | Article, BreadcrumbList, City, CommunityHealth, ContactPoint, MedicalCondition,  | 9 (no) | 2 | aetna, bcbs, cigna, unitedhealthcare, humana, tricare | yes | joint_commission | yes | 7 | 51/53 |
| www.recoveryunplugged.com/location/drug-rehab-in-nashville | 67 | yes | 1 | 2247 | 21 | yes | BreadcrumbList, EntryPoint, MedicalBusiness, Organization, Person, Place, Produc | 3 (yes) | 2 | - | yes | - | yes | 19 | 24/33 |
| southeastaddictiontn.com | 59 | yes | 1 | 1556 | 14 | no | BreadcrumbList, EntryPoint, Organization, PropertyValueSpecification, ReadAction | 5 (yes) | 1 | - | yes | - | yes | 5 | 25/41 |
| www.liveagaindetox.com | 56 | yes | 1 | 2504 | 8 | no | BreadcrumbList, City, ContactPoint, LocalBusiness, MedicalClinic, MedicalOrganiz | 9 (yes) | 0 | aetna, bcbs, cigna, unitedhealthcare | yes | joint_commission, legitscript | yes | 13 | 32/100 |
| www.recoveryranch.com | 54 | yes | 2 | 851 | 7 | no | GeoCoordinates, Off, Organization, Place, PostalAddress, SearchAction, WebPage,  | 4 (yes) | 0 | - | yes | - | yes | 7 | 36/82 |
| thenextdoorrecovery.org | 82 | yes | 2 | 743 | 15 | yes | BreadcrumbList, EntryPoint, Organization, PropertyValueSpecification, ReadAction | 5 (yes) | 1 | - | yes | - | no | 11 | 2/28 |
| **www.cumberlandheights.org** | 25 | no | 1 | 2283 | 18 | no | BreadcrumbList, ContactPoint, EducationalOccupationalCredential, EntryPoint, Geo | 7 (yes) | 3 | - | no | - | yes | 6 | 52/69 |
| **www.cumberlandheights.org/treatment/residential-care** | 37 | no | 1 | 804 | 13 | no | BreadcrumbList, EntryPoint, Organization, PropertyValueSpecification, ReadAction | 7 (yes) | 3 | cigna | yes | - | no | 0 | 38/43 |
| **www.cumberlandheights.org/treatment/drug-and-alcohol-detox** | 41 | no | 1 | 1798 | 12 | yes | Answer, BreadcrumbList, EntryPoint, FAQPage, Organization, PropertyValueSpecific | 8 (yes) | 3 | cigna | no | - | yes | 0 | 18/18 |
| **www.cumberlandheights.org/admissions/insurance-and-finances** | 43 | no | 1 | 675 | 13 | no | BreadcrumbList, EntryPoint, Organization, PropertyValueSpecification, ReadAction | 7 (yes) | 3 | aetna, bcbs, cigna | no | joint_commission | yes | 0 | 21/21 |

## What the winners do that the audited site does not

- 6/6 competitor pages have a title naming a service and Nashville/Tennessee; 0/4 audited pages do.
- 6/6 competitor pages name Nashville/Tennessee in the H1; 1/4 audited pages do.
- 3/6 competitor pages carry an FAQ block (3+ question headings or FAQPage schema); 1/4 audited pages do.
- 6/6 competitor pages state 24/7 / 24-hour availability; 1/4 audited pages do.
- 4/6 competitor pages emit a local entity type in JSON-LD (LocalBusiness/MedicalClinic/Place/City); 1/4 audited pages do.
- Median competitor page has 11 review/testimonial markers vs 0 on the audited pages.
- Median competitor page has 2247 main-content words vs 1798 on the audited pages.
- Median competitor page has 59 title characters vs 41 on the audited pages.

## Entity scores

0-100 from JSON-LD and visible-text signals in the raw HTML (no JS rendering). Points per signal: Organization or MedicalOrganization JSON-LD 10; LocalBusiness/MedicalClinic/MedicalBusiness/Hospital JSON-LD type 10; schema telephone 5; schema address / PostalAddress 5; schema geo 5; schema openingHours(Specification) 5; schema sameAs with 3+ links 10; aggregateRating or Review schema 10; FAQPage schema 10; Person or author schema 5; phone number visible in page text 5; street address with city/state/zip visible in page text 5; 'Nashville' 5+ times in body text 5; Joint Commission/CARF/LegitScript mentioned 5; meta description present, 70-160 chars 5. 'unknown' (audited-page fetch failed, values from the saved JSON) scores 0.

| Page | Score | Failed signals |
|---|---|---|
| **cumberlandheights.org** | 60 | aggregateRating or Review schema, FAQPage schema, Person or author schema, 'Nashville' 5+ times in body text, Joint Commission/CARF/LegitScript mentioned, meta description present, 70-160 chars |
| **cumberlandheights.org/treatment/drug-and-alcohol-detox** | 30 | LocalBusiness/MedicalClinic/MedicalBusiness/Hospital JSON-LD type, schema telephone, schema address / PostalAddress, schema geo, schema openingHours(Specification), schema sameAs with 3+ links, aggregateRating or Review schema, Person or author schema, 'Nashville' 5+ times in body text, Joint Commission/CARF/LegitScript mentioned, meta description present, 70-160 chars |
| **cumberlandheights.org/admissions/insurance-and-finances** | 25 | LocalBusiness/MedicalClinic/MedicalBusiness/Hospital JSON-LD type, schema telephone, schema address / PostalAddress, schema geo, schema openingHours(Specification), schema sameAs with 3+ links, aggregateRating or Review schema, FAQPage schema, Person or author schema, 'Nashville' 5+ times in body text, meta description present, 70-160 chars |
| **cumberlandheights.org/treatment/residential-care** | 20 | LocalBusiness/MedicalClinic/MedicalBusiness/Hospital JSON-LD type, schema telephone, schema address / PostalAddress, schema geo, schema openingHours(Specification), schema sameAs with 3+ links, aggregateRating or Review schema, FAQPage schema, Person or author schema, 'Nashville' 5+ times in body text, Joint Commission/CARF/LegitScript mentioned, meta description present, 70-160 chars |
| apex.rehab/tennessee/nashville | 65 | LocalBusiness/MedicalClinic/MedicalBusiness/Hospital JSON-LD type, schema geo, aggregateRating or Review schema, FAQPage schema |
| recoveryunplugged.com/location/drug-rehab-in-nashville | 65 | schema address / PostalAddress, schema geo, schema openingHours(Specification), FAQPage schema, street address with city/state/zip visible in page text, Joint Commission/CARF/LegitScript mentioned |
| liveagaindetox.com | 60 | schema geo, schema openingHours(Specification), schema sameAs with 3+ links, aggregateRating or Review schema, FAQPage schema |
| recoveryranch.com | 45 | LocalBusiness/MedicalClinic/MedicalBusiness/Hospital JSON-LD type, schema telephone, schema openingHours(Specification), aggregateRating or Review schema, FAQPage schema, Person or author schema, 'Nashville' 5+ times in body text, Joint Commission/CARF/LegitScript mentioned |
| southeastaddictiontn.com | 40 | LocalBusiness/MedicalClinic/MedicalBusiness/Hospital JSON-LD type, schema telephone, schema address / PostalAddress, schema geo, schema openingHours(Specification), aggregateRating or Review schema, FAQPage schema, Person or author schema, Joint Commission/CARF/LegitScript mentioned |
| thenextdoorrecovery.org | 25 | LocalBusiness/MedicalClinic/MedicalBusiness/Hospital JSON-LD type, schema telephone, schema address / PostalAddress, schema geo, schema openingHours(Specification), schema sameAs with 3+ links, aggregateRating or Review schema, FAQPage schema, Person or author schema, Joint Commission/CARF/LegitScript mentioned, meta description present, 70-160 chars |

## On-page strategy signals

| Page | URL path | City/svc int. links (unique) | Nav: locations / programs | Insurers (logos) | CTAs | Schema rating | Testimonial blocks | 24/7 | Videos | H2s |
|---|---|---|---|---|---|---|---|---|---|---|
| apex.rehab/tennessee/nashville | `/tennessee/nashville/` | 362 (273) | no / yes | 11 (12) | tel, form, verify_insurance | - | 0 | yes | 0 | 17 |
| recoveryunplugged.com/location/drug-rehab-in-nashville | `/location/drug-rehab-in-nashville/` | 160 (43) | yes / yes | 0 (3) | tel, form, verify_insurance | 5 (610) | 1 | yes | 0 | 28 |
| southeastaddictiontn.com | `/` | 56 (38) | no / yes | 0 (9) | tel, form, verify_insurance | - | 3 | yes | 0 | 14 |
| liveagaindetox.com | `/` | 197 (62) | no / yes | 7 (6) | tel, verify_insurance | - | 1 | yes | 0 | 8 |
| recoveryranch.com | `/` | 54 (30) | no / yes | 0 (16) | tel, verify_insurance | - | 0 | yes | 0 | 7 |
| thenextdoorrecovery.org | `/` | 27 (3) | no / yes | 1 (0) | tel, form | - | 4 | yes | 0 | 15 |
| **cumberlandheights.org** | `/` | 74 (19) | yes / yes | 0 (8) | tel, form, verify_insurance | - | 6 | no | 1 | 18 |
| **cumberlandheights.org/treatment/residential-care** | `/treatment/residential-care/` | 70 (17) | yes / yes | 1 (0) | tel, form | - | 0 | yes | 0 | 13 |
| **cumberlandheights.org/treatment/drug-and-alcohol-detox** | `/treatment/drug-and-alcohol-detox/` | 72 (17) | yes / yes | 1 (8) | tel, form, verify_insurance | - | 0 | no | 0 | 12 |
| **cumberlandheights.org/admissions/insurance-and-finances** | `/admissions/insurance-and-finances/` | 70 (17) | yes / yes | 3 (9) | tel, form, verify_insurance | - | 0 | no | 0 | 13 |

## What each competitor's on-page strategy is

### apex.rehab/tennessee/nashville

- URL pattern: dedicated `/tennessee/nashville/` page with the city/state in the path; title "Drug And Alcohol Addiction Rehab In Nashville, TN" (service + geo), H1 "Drug and Alcohol Rehab Centers in Nashville, TN".
- Outline: 7239 main-content words, 17 H2s: "Apex Recovery Centers in Tennessee" / "APEX Recovery Facilities Near Nashville: Bren" / "Outpatient Rehab in Greater Nashville, TN" / "Inpatient Rehab facility Near Nashville, TN" / "What Are Rehabilitation Programs for Drug & A".
- CTAs: tel, form, verify_insurance; 9 tel: links, 2 <form> + form embed script, 24/7 stated.
- Proof: entity score 65/100; no rating in schema; 0 testimonial/review blocks; accreditations: joint_commission; 11 insurers named (12 insurer logos by alt text).
- Local signals: 'Nashville' x173; visible phone yes, street address yes; local schema type no; 362 internal links with city/service terms (273 unique URLs); nav exposes locations no, programs yes.

### recoveryunplugged.com/location/drug-rehab-in-nashville

- URL pattern: dedicated `/location/drug-rehab-in-nashville/` page with the city/state in the path; title "Nashville Drug and Alcohol Rehab | Addiction Treatment in Tennessee" (service + geo), H1 "NASHVILLE DRUG & ALCOHOL REHAB".
- Outline: 2247 main-content words, 28 H2s: "Welcome To Recovery Unplugged." / "Locations" / "TAKE THE FIRST STEP TOWARDS RECOVERY CALL 1-8" / "Taking The First Step." / "TAKE THE FIRST STEP TOWARDS RECOVERY CALL 1-8".
- CTAs: tel, form, verify_insurance; 3 tel: links (one in <header>), 3 <form> + form embed script, 24/7 stated.
- Proof: entity score 65/100; aggregateRating 5 from 610 reviews in schema; 1 testimonial/review blocks; accreditations: none named; 0 insurers named (3 insurer logos by alt text).
- Local signals: 'Nashville' x40; visible phone yes, street address no; local schema type yes; 160 internal links with city/service terms (43 unique URLs); nav exposes locations yes, programs yes.

### southeastaddictiontn.com

- URL pattern: ranks with its homepage (`/`), so the whole domain is the Nashville page; title "Drug & Alcohol Rehab in Nashville, TN | Southeast Addiction" (service + geo), H1 "Drug & Alcohol Rehab in Nashville, TN".
- Outline: 1556 main-content words, 14 H2s: "Addiction Help From People You Can Trust" / "The addiction help you deserve." / "What Our Clients Are Saying" / "Most Insurances Accepted" / "Tour Our Facilities".
- CTAs: tel, form, verify_insurance; 5 tel: links (one in <header>), 1 <form> + form embed script, 24/7 stated.
- Proof: entity score 40/100; no rating in schema; 3 testimonial/review blocks; accreditations: none named; 0 insurers named (9 insurer logos by alt text).
- Local signals: 'Nashville' x29; visible phone yes, street address yes; local schema type no; 56 internal links with city/service terms (38 unique URLs); nav exposes locations no, programs yes.

### liveagaindetox.com

- URL pattern: ranks with its homepage (`/`), so the whole domain is the Nashville page; title "Drug & Alcohol Detox in Nashville, TN | Live Again Detox" (service + geo), H1 "Drug & Alcohol Detox & Addiction Treatment in Nashville, TN".
- Outline: 2504 main-content words, 8 H2s: "Yes , Your Insurance Covers Detox and Rehab T" / "We accept most major insurance" / "Drug & Alcohol Detox in Nashville, TN" / "Drug & Alcohol Detox Rehab in Nashville, TN" / "Meet the Team at Live Again Detox".
- CTAs: tel, verify_insurance; 9 tel: links (one in <header>), 0 <form>, 24/7 stated.
- Proof: entity score 60/100; no rating in schema; 1 testimonial/review blocks; accreditations: joint_commission, legitscript; 7 insurers named (6 insurer logos by alt text).
- Local signals: 'Nashville' x90; visible phone yes, street address yes; local schema type yes; 197 internal links with city/service terms (62 unique URLs); nav exposes locations no, programs yes.

### recoveryranch.com

- URL pattern: ranks with its homepage (`/`), so the whole domain is the Nashville page; title "Drug & Alcohol Rehab Near Nashville, TN | The Ranch TN" (service + geo), H1 "A better life begins at The Ranch Tennessee.".
- Outline: 851 main-content words, 7 H2s: "We Are In-Network with" / "Care you can trust, shaped by real experience" / "Support for every part of you" / "Getting started is simple" / "Connect with The Ranch Tennessee".
- CTAs: tel, verify_insurance; 4 tel: links (one in <header>), 0 <form>, 24/7 stated.
- Proof: entity score 45/100; no rating in schema; 0 testimonial/review blocks; accreditations: none named; 0 insurers named (16 insurer logos by alt text).
- Local signals: 'Nashville' x2; visible phone yes, street address yes; local schema type no; 54 internal links with city/service terms (30 unique URLs); nav exposes locations no, programs yes.

### thenextdoorrecovery.org

- URL pattern: ranks with its homepage (`/`), so the whole domain is the Nashville page; title "Safe Treatment Facility For Women • The Next Door • Nashville • Next D" (service + geo), H1 "Safe Treatment Facility For Women • The Next Door • Nashvill".
- Outline: 743 main-content words, 15 H2s: "Empowering women for lifetime recovery" / "How we help" / "Our Services" / "Alumni Stories" / "Meet Nikki".
- CTAs: tel, form; 5 tel: links (one in <header>), 1 <form> + form embed script, 24/7 stated.
- Proof: entity score 25/100; no rating in schema; 4 testimonial/review blocks; accreditations: none named; 1 insurers named (0 insurer logos by alt text).
- Local signals: 'Nashville' x8; visible phone yes, street address yes; local schema type no; 27 internal links with city/service terms (3 unique URLs); nav exposes locations no, programs yes.

## What Cumberland Heights should copy first

Ordered by how many competitors do it, then by cost; only items where competitors lead the audited pages.

1. **24/7 availability stated**: 6/6 competitors do it, 1/4 of our pages do (cost: low). Fix: put '24/7 admissions' next to the header phone.
2. **meta description 70-160 chars**: 5/6 competitors do it, 0/4 of our pages do (cost: low). Fix: write service + Nashville meta descriptions.
3. **insurer logos with alt text**: 5/6 competitors do it, 3/4 of our pages do (cost: low). Fix: add an in-network logo strip with alt text naming each insurer.
4. **'Nashville' 5+ times in body**: 5/6 competitors do it, 0/4 of our pages do (cost: medium). Fix: work Nashville/Middle Tennessee into H2s and body copy.
5. **'Verify insurance' CTA**: 5/6 competitors do it, 3/4 of our pages do (cost: medium). Fix: add a 'Verify insurance' button linking to a short benefits form.
6. **sameAs with 3+ profiles**: 4/6 competitors do it, 1/4 of our pages do (cost: low). Fix: list GBP, Facebook, LinkedIn, YouTube, Instagram in sameAs.
