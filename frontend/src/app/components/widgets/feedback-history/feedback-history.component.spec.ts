import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { FeedbackHistoryComponent } from './feedback-history.component';

describe('FeedbackHistoryComponent', () => {
  let component: FeedbackHistoryComponent;
  let fixture: ComponentFixture<FeedbackHistoryComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ FeedbackHistoryComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(FeedbackHistoryComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
