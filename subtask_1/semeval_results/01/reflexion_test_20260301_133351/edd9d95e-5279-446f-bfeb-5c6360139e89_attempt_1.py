% Facts for witnesses
cloud(cloud1).

% Rules from premises
politician(X) :- cloud(X).
made_of_cotton_candy(X) :- politician(X).

% Validity check for conclusion: Some things made of cotton candy are clouds
valid_syllogism :- made_of_cotton_candy(X), cloud(X).