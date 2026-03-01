% Witness: a violin that is both a string instrument and a musical instrument
violin(violin1).

% Rules from the A-premises
string_instrument(X) :- violin(X).
musical_instrument(X) :- violin(X).

% Validity check: Some musical instruments are string instruments
valid_syllogism :- musical_instrument(X), string_instrument(X).