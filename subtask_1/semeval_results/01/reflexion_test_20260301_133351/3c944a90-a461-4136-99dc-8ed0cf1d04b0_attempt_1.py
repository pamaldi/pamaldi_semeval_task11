% Witnesses
person(alice).

% Rules from premises
medical_professional(X) :- doctor(X).
has_degree(X) :- medical_professional(X).

% doctor has facts to exist
doctor(alice).

% Validity check: Some people with degrees are doctors
valid_syllogism :- has_degree(X), doctor(X).