% This syllogism is INVALID due to contradictory premises
% The premises are:
% 1. All seas are large bodies of saltwater (A: All S are P)
% 2. No rivers are large bodies of saltwater (E: No S is P)
% 3. All rivers are seas (A: All S are P)

% This creates a contradiction because if all rivers are seas (premise 3)
% and all seas are large bodies of saltwater (premise 1), then all rivers
% should be large bodies of saltwater - which contradicts premise 2.

% To show the syllogism is INVALID, we need to build a counterexample
% where the premises are TRUE but the conclusion is FALSE

% Witness for a river
river(nile).

% Witness for a sea that is NOT a river (to make seas and rivers disjoint)
sea(mediterranean).

% Rule from premise 3: All rivers are seas (A-type)
sea(X) :- river(X).

% Rule from premise 1: All seas are large bodies of saltwater (A-type)
large_body_of_saltwater(X) :- sea(X).

% Fail clause for premise 2: No rivers are large bodies of saltwater (E-type)
% Since we have a river(nile), we don't need a fail clause for large_body_of_saltwater/1
% because we're making it false by not asserting it for the nile

% Validity check: Check if the conclusion is FALSE in this model
% The conclusion is implied to be "All rivers are large bodies of saltwater"
% In our counterexample, this is FALSE because nile is a river that is NOT a large body of saltwater
valid_syllogism :- river(nile), \+ large_body_of_saltwater(nile).