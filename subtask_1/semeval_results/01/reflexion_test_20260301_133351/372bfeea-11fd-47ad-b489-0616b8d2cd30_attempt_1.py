% Facts
cloud(c1).
cumulus(c1).

% Rule from first premise: All clouds are made of solid iron
solid_iron(X) :- cloud(X).

% Validity check: Some cumulus clouds are solid iron
valid_syllogism :- cumulus(X), solid_iron(X).