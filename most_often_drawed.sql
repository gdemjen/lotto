SELECT number, COUNT(*) AS times_drawn                                                                                                                                                                  
  FROM (                                                                                                                                                                                                  
      SELECT num1 AS number FROM draws                                                                                                                                                                    
      UNION ALL                                                                                                                                                                                           
      SELECT num2 FROM draws                                                                                                                                                                              
      UNION ALL                                                                                                                                                                                           
      SELECT num3 FROM draws                                
      UNION ALL
      SELECT num4 FROM draws
      UNION ALL
      SELECT num5 FROM draws
  )
  GROUP BY number
  ORDER BY times_drawn DESC
  LIMIT 5;