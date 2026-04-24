  SELECT number, COUNT(*) AS times_drawn                                                                                                                                                                  
  FROM (
      SELECT num1 AS number FROM draws_otos                                                                                                                                                               
      UNION ALL                                             
      SELECT num2 FROM draws_otos
      UNION ALL
      SELECT num3 FROM draws_otos
      UNION ALL
      SELECT num4 FROM draws_otos
      UNION ALL
      SELECT num5 FROM draws_otos
  )
  GROUP BY number
  ORDER BY times_drawn DESC
  LIMIT 5;