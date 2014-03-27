library(ggplot2)
library(RColorBrewer)


cleanup <- function(df) {
  df$round_num <- as.factor(df$round_num)
  df$rank_diff <- as.factor(df$rank_diff)
  #df$cluster_num <- as.factor(df$cluster_num)
  
  return(df)
}

plot_timeline <- function(df) {
  # Opacity based on rank diff?
  # Opacity based on upset?
  min_diff <- min(df$diff_score)
  max_diff <- max(df$diff_score)
  max_time <- max(df$time)
  
  round_two <- which(df$round == 2)
  round_three <- which(df$round == 3)
  
  g <- ggplot(df[, ], aes(x = time, y = diff_score)) +
    geom_line(aes(color = rank_diff, group = game_id)) +
    geom_hline(yintercept=0) +
    scale_x_continuous("Time (minutes)", limits = c(0, max_time)) +
    # If only plotting subsets of all games, keep axis constant
    scale_y_continuous("Score Differential", limits = c(min_diff, max_diff)) +
    scale_colour_brewer("Rank Difference", type="seq", palette="RdBu") +
    # Make colors pop with a black background
    #theme(panel.background = element_rect(fill = "black")) +
    ggtitle('NCAA 2014: Rounds 2 and 3')
  
  print(g)
}

heatmap <- function(df, max_score=15) {
  df$rounded_diff_score <- sapply(df$diff_score, function(score) {
    ifelse(score > 0, min(score, max_score), max(score, -max_score))
  })
  
  # Thanks to tutorial here: http://learnr.wordpress.com/2010/01/26/ggplot2-quick-heatmap-plotting/
  # Also good: http://quantcorner.wordpress.com/2013/11/02/creating-a-heatmap-to-visualize-returns-with-r-ggplot2/
  
  heat <- ggplot(df, aes(time, game_id)) +
    geom_tile(aes(fill = rounded_diff_score), color = 'white') +
    scale_fill_gradient2("Score Differential", low = 'red', high = 'blue') +
    # TODO add a label for facets
    facet_grid(rank_diff ~ ., scales = 'free', space = 'free') +
    theme_bw() +
    scale_x_continuous('Time') +
    scale_y_discrete('Teams') +
    ggtitle('NCAA 2014: Rounds 2 and 3')
  
  print(heat)
}