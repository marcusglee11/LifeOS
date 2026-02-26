from __future__ import annotations

import pytest
from runtime.orchestration.loop.budgets import BudgetConfig, BudgetController


class TestBudgetConfig:
    """Test suite for BudgetConfig validation."""
    
    def test_valid_config_passes(self) -> None:
        """Test that valid configurations are accepted."""
        # Default values should pass
        config = BudgetConfig()
        assert config.max_attempts == 5
        assert config.max_tokens == 100000
        assert config.max_wall_clock_minutes == 30
        
        # Custom valid values should pass
        config = BudgetConfig(
            max_attempts=10,
            max_tokens=200000,
            max_wall_clock_minutes=60
        )
        assert config.max_attempts == 10
        assert config.max_tokens == 200000
        assert config.max_wall_clock_minutes == 60
    
    def test_max_attempts_negative_raises(self) -> None:
        """Test that negative max_attempts raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            BudgetConfig(max_attempts=-1)
        assert "max_attempts must be positive" in str(exc_info.value)
        assert "-1" in str(exc_info.value)
    
    def test_max_attempts_zero_raises(self) -> None:
        """Test that zero max_attempts raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            BudgetConfig(max_attempts=0)
        assert "max_attempts must be positive" in str(exc_info.value)
        assert "0" in str(exc_info.value)
    
    def test_max_tokens_zero_raises(self) -> None:
        """Test that zero max_tokens raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            BudgetConfig(max_tokens=0)
        assert "max_tokens must be positive" in str(exc_info.value)
        assert "0" in str(exc_info.value)
    
    def test_max_tokens_negative_raises(self) -> None:
        """Test that negative max_tokens raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            BudgetConfig(max_tokens=-100)
        assert "max_tokens must be positive" in str(exc_info.value)
        assert "-100" in str(exc_info.value)
    
    def test_max_wall_clock_minutes_zero_raises(self) -> None:
        """Test that zero max_wall_clock_minutes raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            BudgetConfig(max_wall_clock_minutes=0)
        assert "max_wall_clock_minutes must be positive" in str(exc_info.value)
        assert "0" in str(exc_info.value)
    
    def test_max_wall_clock_minutes_negative_raises(self) -> None:
        """Test that negative max_wall_clock_minutes raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            BudgetConfig(max_wall_clock_minutes=-5)
        assert "max_wall_clock_minutes must be positive" in str(exc_info.value)
        assert "-5" in str(exc_info.value)
    
    def test_budget_controller_integration(self) -> None:
        """Test that BudgetConfig integrates properly with BudgetController."""
        # Create valid config
        config = BudgetConfig(
            max_attempts=3,
            max_tokens=1000,
            max_wall_clock_minutes=10
        )
        
        # Pass to BudgetController
        controller = BudgetController(config=config)
        
        # Verify controller uses config
        assert controller.config.max_attempts == 3
        assert controller.config.max_tokens == 1000
        assert controller.config.max_wall_clock_minutes == 10
        
        # Test check_budget functionality
        is_over, reason = controller.check_budget(
            current_attempt=1,
            total_tokens=500,
            token_accounting_available=True
        )
        assert not is_over
        assert reason is None
        
        # Test exceeding attempt budget
        is_over, reason = controller.check_budget(
            current_attempt=4,
            total_tokens=500,
            token_accounting_available=True
        )
        assert is_over
        assert reason is not None
    
    def test_budget_controller_with_default_config(self) -> None:
        """Test that BudgetController works with default config."""
        controller = BudgetController()
        
        # Verify default config is used
        assert controller.config.max_attempts == 5
        assert controller.config.max_tokens == 100000
        assert controller.config.max_wall_clock_minutes == 30
        
        # Verify functionality
        is_over, reason = controller.check_budget(
            current_attempt=1,
            total_tokens=1000,
            token_accounting_available=True
        )
        assert not is_over
        assert reason is None
