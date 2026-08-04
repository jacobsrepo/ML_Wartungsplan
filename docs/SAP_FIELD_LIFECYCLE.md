# SAP field lifecycle used by this repository

## Existing before maintenance-plan entry

These are master-data objects that already exist and are selected during plan
creation:

- `Verantwortlicher Arbeitsplatz (CRHD.ARBPL)`
- `Technischer Platz (ILOA.TPLNR)`
- `Bezeichnung technischer Platz (IFLOTX.PLTXT)`
- `Equipment (MPOS.EQUNR)`
- `Equipment-Kurztext (EQKT.EQKTX)`
- `Plangruppentyp (MPOS.PLNTY)`
- `Plangruppe (MPOS.PLNNR)`
- `Plangruppenzähler (MPOS.PLNAL)`

## Selected, entered or generated during maintenance-plan creation

- `Wartungsplan (MPLA.WARPL)`
- `Wartungsposition (MPOS.WAPOS)`
- `Kurztext Wartungsposition (MPOS.PSTXT)`
- work-centre assignment
- technical-location assignment
- equipment assignment
- task-list assignment
- `Aktuelle Wartungsstrategie (MPLA.STRAT)`
- `MPLA.VSPOS`
- `MPLA.TOPOS`
- `MPLA.VSNEG`
- `MPLA.TONEG`
- `MPLA.SFAKT`
- `MPLA.FABKL`
- `MPLA.HORIZ`
- `MPLA.HORIZ_DAYS`
- `MPLA.HORIZ_QUALIFIER`
- `MPLA.ABRHO`
- `MPLA.HUNIT`
- `MPLA.CALL_CONFIRM`
- `MPLA.STADT`

## Generated later through scheduling and order processing

- `Abrufnummer (MHIO.ABNUM)`
- `Abrufdatum (MHIS.ABRUD)`
- `Plandatum (MHIS.NPLDA)`
- `Auftrag (AUFK.AUFNR)`
- `Eckstart (AFKO.GSTRP)`
- `Eckende (AFKO.GLTRP)`
- `EROF (AUFK.PHAS0)`
- `Frei (AUFK.PHAS1)`
- `GETRI (AFKO.GETRI)`
- `IDAT2 (AUFK.IDAT2)`
- `IDAT3 (AUFK.IDAT3)`

## Calculated outside direct SAP entry

- `Abschlussdatum (AUFK.IDAT2/IDAT3)`
- maintenance cycle in days
- call-to-plan processing time
- call-to-Eckende processing time
- delay against planned date
- delay against Eckende
- ON_TIME / NOT_IN_TIME KPI
- calendar-week/weekday display text
- SAP web link
- snapshot/history explanatory fields

The model must not use completion dates, final status, KPI or delay columns as
inputs because those values are unavailable when the recommendation is made.
