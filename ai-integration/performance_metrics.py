import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

class AgentPerformanceHeatmap:
    def __init__(self):
        self.metrics = {
            'response_time': [],
            'success_rate': [],
            'resource_usage': [],
            'task_completion': [],
            'accuracy': []
        }
        self.agents = [
            'MarketIntelligence',
            'LegalCompliance', 
            'CustomerExperience',
            'Operations',
            'RiskAssessment'
        ]
        
    def generate_sample_data(self):
        """Generate sample performance data for demonstration"""
        np.random.seed(42)
        data = []
        
        # Generate 24 hours of data points
        for hour in range(24):
            for agent in self.agents:
                data.append({
                    'agent': agent,
                    'hour': hour,
                    'efficiency_score': np.random.normal(0.75, 0.15),
                    'timestamp': datetime.now() - timedelta(hours=24-hour)
                })
                
        return pd.DataFrame(data)

    def plot_heatmap(self, save_path='agent_performance_heatmap.png'):
        """Generate and save the performance heatmap"""
        # Get or generate performance data
        df = self.generate_sample_data()
        
        # Pivot the data for the heatmap
        pivot_data = df.pivot(
            index='agent', 
            columns='hour', 
            values='efficiency_score'
        )
        
        # Set up the matplotlib figure
        plt.figure(figsize=(15, 8))
        
        # Create heatmap using seaborn
        sns.heatmap(
            pivot_data,
            cmap='RdYlGn',  # Red (low) to Yellow (mid) to Green (high)
            center=0.75,    # Center point for color scaling
            vmin=0,         # Minimum value
            vmax=1,         # Maximum value
            annot=True,     # Show values in cells
            fmt='.2f',      # Format for values
            cbar_kws={'label': 'Efficiency Score'}
        )
        
        # Customize the plot
        plt.title('Agent Performance Heatmap (24-Hour Period)')
        plt.xlabel('Hour of Day')
        plt.ylabel('Agent Type')
        
        # Save the plot
        plt.tight_layout()
        plt.savefig(save_path)
        plt.close()
        
        return save_path

    def update_metrics(self, agent_name, metrics_data):
        """Update performance metrics for a specific agent"""
        if agent_name not in self.agents:
            raise ValueError(f"Unknown agent: {agent_name}")
            
        for metric, value in metrics_data.items():
            if metric in self.metrics:
                self.metrics[metric].append({
                    'agent': agent_name,
                    'value': value,
                    'timestamp': datetime.now()
                })

def main():
    # Create an instance of the heatmap generator
    heatmap = AgentPerformanceHeatmap()
    
    # Generate and save a sample heatmap
    output_path = heatmap.plot_heatmap()
    print(f"Heatmap saved to: {output_path}")

if __name__ == "__main__":
    main()
