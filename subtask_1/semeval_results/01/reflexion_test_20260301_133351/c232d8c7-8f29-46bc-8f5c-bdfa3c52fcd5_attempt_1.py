% Witness for river
river(nile).

% Fail clause for rivers being large bodies of saltwater
large_body_of_saltwater(X) :- fail.

% Rules from premises
sea(X) :- river(X).

% Validity check: Check if "Every river is a sea" leads to contradiction with "Rivers are not large bodies of saltwater"
valid_syllogism :- river(X), sea(X), \+ large_body_of_saltwater(X).