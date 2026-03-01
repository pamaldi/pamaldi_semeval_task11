piano(p1).

% musical_instrument has NO facts in this counterexample
musical_instrument(_) :- fail.

% object has facts that are NOT pianos
object(p1).  % p1 is a piano (so it's an object)
object(o1).  % o1 is an object that is NOT a piano

% Rules from premises
musical_instrument(X) :- piano(X).  % All pianos are musical instruments
object(X) :- musical_instrument(X).  % All musical instruments are objects

% Validity check: Some objects are pianos (should fail in valid counterexample)
valid_syllogism :- object(X), piano(X).