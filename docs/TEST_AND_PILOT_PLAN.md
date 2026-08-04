# Test and pilot plan

## Offline evaluation

1. Build the completed-order dataset.
2. Train on older orders and test only on the newest orders.
3. Compare Q80, Q85 and Q90.
4. Measure:
   - achieved ON_TIME coverage
   - average recommended extension
   - unnecessary padding
   - remaining late orders
   - performance by work centre and strategy
5. Review high-impact mistakes with planners.

## Shadow pilot

For four to eight weeks:

- generate recommendations
- send email to planners
- do not change SAP automatically
- record accepted deadline, override and reason
- compare recommendation with actual completion

## Controlled operational pilot

Use one or two work centres.

Success requires both:

- higher ON_TIME rate
- no unacceptable increase in deadline padding

## Stop conditions

Pause the pilot when:

- missing or inconsistent dates increase
- recommendations are frequently capped
- planners reject most recommendations
- one work centre performs materially worse
- the model encourages deadlines that overlap the next maintenance cycle
