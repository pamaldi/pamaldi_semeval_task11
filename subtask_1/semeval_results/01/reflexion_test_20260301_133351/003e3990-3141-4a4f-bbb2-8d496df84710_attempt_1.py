% Facts for I-proposition (Some percussion instruments are musical instruments)
musical_instrument(triangle).
percussion_instrument(triangle).

% Fail clause for percussion_instrument with strings (E-proposition: No percussion has strings)
conflict :- percussion_instrument(X), has_strings(X).
has_strings(_) :- fail.

% Rule from A-proposition (All percussion instruments are musical instruments)
% Not needed, since we have a specific witness

% Validity check: Some musical instruments do not have strings (O-proposition)
valid_syllogism :- musical_instrument(X), \+ has_strings(X).