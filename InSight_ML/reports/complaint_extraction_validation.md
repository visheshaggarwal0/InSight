# Complaint Extraction Validation

**Dataset**: `cosmetics_10k.csv` (first 1000 reviews — real Sephora cosmetics data)

- Reviews processed: 1000
- Detections: 465 (46.5%)
- No complaint extracted: 535 (53.5%)

> **IMPORTANT**: Detection rate is a coverage metric only. Without manually
> labelled complaint spans there is no ground truth for precision or recall.
> A high detection rate may indicate false positives (e.g., 'but' in non-complaint
> contexts). Treat this as provisional engineering output.

## Representative Extracted Complaints

- **Review snippet**: `I love how this feels on my face! It’s incredibly hydrating. When I wake up in the morning I can still feel the moisture...`
  **Extracted span**: `but this moisturizes throughout the night.` (offset 193–235)

- **Review snippet**: `I love this product! it works so well for people with oily/acne prone skin. It smells really nice, has a nice feel and m...`
  **Extracted span**: `but it isn’t drying! so great! I received this product complementary for testing purchases and I can’t wait to purchase another one when this one is out!` (offset 220–373)

- **Review snippet**: `Oh my! I am in love with this cleansing oil. I’ve heard of and seen this brand before and it’s definitely worth the hype...`
  **Extracted span**: `until now and I have been missing out. If your skin is lacking moisture or you need that extra glow, then this will do it for you. My skin felt so smooth and luminated  after using this. I would highly recommend.` (offset 157–369)

- **Review snippet**: `I have large pores on my nose and my chin and always despised having them. I received Bye Bye Pores as a #freeproduct fr...`
  **Extracted span**: `Although some large pores won’t magically shrink, the product is very effective at exfoliating and removing any trapped dirt inside the pores. hence making them almost disappear. My nose and chin don’t have any black heads any longer, and I noticed the skin more bright and visibly clean. This is definitely a product to use on an on-going basis. It is fragrance-free and leaves no residue; you may sometimes feel a very slight tingle, but it means the glycolic acid is doing its job. I used it nighty.` (offset 322–824)

- **Review snippet**: `Still have dry skin, but improved a bit....`
  **Extracted span**: `but improved a bit.` (offset 21–40)
