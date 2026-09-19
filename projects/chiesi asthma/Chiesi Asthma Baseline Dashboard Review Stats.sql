select
#Title Page
	curdate() as `Report Date`,

#ASTHMA PREVALENCE & REGISTER ANALYSIS
	count(A2PR_ID) as AsthmaPatients,
	l.LOC_ListSize as Pop,
	sum(A2PR_Gender = 1) as Males,
	sum(A2PR_Gender = 2) as Females,
	count(A2PR_ID) / l.LOC_ListSize as `Asthma prev`,
	sum(A2PR_NewDiagAst12m = 1) as `Asthma diag after 1 April 2025`,
    coalesce(sum((A2PR_Feno12m > 0) or (A2PR_EosinophilDate > 0) or (A2PR_Spirometry12Mo > 0) or (A2PR_PeakFlow12m > 0)),0) as `At least 1 test`,
    coalesce(sum((A2PR_Feno12m > 0) or (A2PR_EosinophilDate > 0) or (A2PR_Spirometry12Mo > 0) or (A2PR_PeakFlow12m > 0)),0) / count(A2PR_ID) as `At least 1 test %`,
    coalesce(sum((A2PR_NdxFeno > 0 and A2PR_NewDiagAst12m = 1) or (A2PR_NdxEos > 0 and A2PR_NewDiagAst12m = 1) or (A2PR_NdxSpiro > 0 and A2PR_NewDiagAst12m = 1) or (A2PR_NdxPefr > 0 and A2PR_NewDiagAst12m = 1)),0) as `Diag this QOF year with at least 1 test within 6m of diag`,
	coalesce(sum((A2PR_NdxFeno > 0 and A2PR_NewDiagAst12m = 1) or (A2PR_NdxEos > 0 and A2PR_NewDiagAst12m = 1) or (A2PR_NdxSpiro > 0 and A2PR_NewDiagAst12m = 1) or (A2PR_NdxPefr > 0 and A2PR_NewDiagAst12m = 1)),0) / sum(A2PR_NewDiagAst12m = 1) as `Diag this QOF year with at least 1 test within 6m of diag %`,
	sum(A2PR_AstReview12Mo = 2) as `Ast review in past 12m`,
	sum(A2PR_AstReview12Mo = 2) / count(A2PR_ID) as `Ast review in past 12m %`,

#BASELINE ASTHMA CARE MARKERS (INCLUDES ALL PATIENTS ON THE ASTHMA REGISTER)
	sum(A2PR_SmokingStat12Mo = 2) as `Smoking stat record 12m`,
	sum(A2PR_SmokingStat12Mo = 2) / count(A2PR_ID) as `Smoking stat record 12m %`,
	sum(A2PR_SmokingStatCalc in (1, 3, 4)) as `current or past smokers`,
	sum(A2PR_SmokingStatCalc in (1, 3, 4)) / count(A2PR_ID) as `current or past smokers %`,
	sum(A2PR_SmokingStatcalc = 3) as `current smokers`,
	sum(A2PR_SmokingStatCalc = 3) / count(A2PR_ID) as `current smokers %`,
	sum(case when A2PR_SmokingStatcalc = 3 then A2PR_SmokingCess12m in (1, 0) end) as `Smokers that have not be offered smoking cess 12m`,
	sum(case when A2PR_SmokingStatCalc = 3 then A2PR_SmokingCess12m in (1, 0) end) / sum(A2PR_SmokingStatcalc = 3) as `Smokers that have not be offered smoking cess 12m %`,
	sum(A2PR_InhalerTech12Mo = 2) as `Ast pts with inhaler tech 12m`,
	sum(A2PR_InhalerTech12Mo = 2) / count(A2PR_ID) as `Ast pts with inhaler tech 12m %`,
	sum(A2PR_InhalerTechCalc in (1, 2)) as `Pts with sub opt inhaler tech`,
	sum(A2PR_InhalerTechCalc in (1, 2)) / count(A2PR_ID) as `Pts with sub opt inhaler tech %`,
	sum(A2PR_InhalerTechCalc is null) as `no record of inhaler tech`,
	sum(A2PR_InhalerTechCalc is null) / count(A2PR_ID) as `no record of inhaler tech %`,
	sum(A2PR_Paap12Mo = 0) as `no PAAP`,
	sum(A2PR_Paap12Mo = 0) / count(A2PR_ID) as `no PAAP %`,

#BASELINE MEASUREMENT OF ASTHMA SYMPTOMS
	sum(A2PR_ActScore12Mo = 2) as `ACT 12m`,
	sum(A2PR_ActScore12Mo = 2) / count(A2PR_ID) as `ACT 12m %`,
	sum(A2PR_ActScore12Mo = 0) as `no record ACT score`,
	sum(A2PR_ActScore12Mo in (1, 2)) as `Has ACT score`,
	sum(A2PR_ActScore12Mo = 0) / count(A2PR_ID) as `no record ACT score %`,
	sum(A2PR_ActValue < 20) as `ACT score <20`,
	sum(A2PR_ActValue < 20) / sum(A2PR_ActScore12Mo in (1, 2)) as `ACT score <20 %`,
	sum(A2PR_AcqScore12m = 2) as `ACQ Score 12m`,
	sum(A2PR_AcqScore12m = 2) / count(A2PR_ID) as `ACQ Score 12m %`,
	sum(A2PR_AcqScoreValue is null) as `no recorded ACQ score`,
	sum(A2PR_AcqScoreValue is not null) as `Has ACQ score`,
	sum(A2PR_AcqScoreValue is null) / count(A2PR_ID) as `no recorded ACQ score %`,
	ifnull(sum(A2PR_AcqScoreValue is not null and A2PR_AcqScoreValue >= 1.5),0) as `ACQ score of >= 1.5`,
	ifnull(sum(A2PR_AcqScoreValue is not null and A2PR_AcqScoreValue >= 1.5) / sum(A2PR_AcqScoreValue is not null),0) as `ACQ score of >= 1.5 %`,
	sum(A2PR_TotalSabaIssues12m >= 3) as `3+SABA 12m`,
	sum(A2PR_TotalSabaIssues12m >= 6) as `6+ SABA 12m`,
	sum(A2PR_TotalSabaIssues12m >= 12) as `12+ SABA 12m`,
	sum(A2PR_SabaDoseDay >= 1 and A2PR_IcsFinal = 0) as `not recieving preventer inhaler that have used >=1 SABA doses/ day 12m`,

#BASELINE ASSESSMENT OF ASTHMA ATTACK/EXACERBATIONS
	sum(A2PR_CohortOcsExacAdmit = 1) as `>=2 OCS and Asthma attacks or >=2 admission due to asthma 12m`,
	sum(A2PR_CohortOcsExacAdmit = 1) / count(A2PR_ID) as `>=2 OCS and Asthma attacks or >=2 admission due to asthma 12m %`,
	sum(A2PR_CohortOcsExacAdmit = 2) as `>=1 OCS or >= 1 asthma attack 12m`,
	sum(A2PR_CohortOcsExacAdmit = 2) / count(A2PR_ID) as `>=1 OCS or >= 1 asthma attack 12m %`,

#BASELINE ASSESSMENT OF CURRENT PHARMACOLOGICAL MANAGEMENT OF ASTHMA
	sum(A2PR_Age >= 18 and A2PR_Cohort1 = 1 and A2PR_PatientCohort = 1) as `for assessment`

from asthma2PatientResults
left join Reviews on R_ID = A2PR_EventID
left join Events on EVENT_ReviewID = R_ID
left join Locations l on l.LOC_ID = R_LocID
left join Locations p on p.LOC_ID = l.LOC_Parent
where EVENT_ID = ${EventID}