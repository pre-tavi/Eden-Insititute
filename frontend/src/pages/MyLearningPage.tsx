import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Badge,
  Button,
  Card,
  CourseCardSkeleton,
  EmptyState,
  ErrorState,
  ProgressBar,
} from "../components/ui";
import { useAuth } from "../context/AuthContext";
import {
  ensureCsrfToken,
  extractApiErrorMessage,
  type EnrollmentItem,
} from "../types/auth";
import { formatMinorCurrency, type PaginatedResponse } from "../types/catalog";

interface PaymentInitiateResponse {
  id: string;
  provider_ref: string;
  checkout_url: string;
  amount_minor: number;
  currency: "KES" | "USD";
  status: string;
}

interface ResidencyBlockItem {
  id: string;
  course: string;
  location: "nairobi" | "embu";
  location_display: string;
  title: string;
  starts_on: string;
  ends_on: string;
  capacity: number;
  seats_remaining: number;
  fee_minor: number;
  fee_major: string;
  currency: "KES" | "USD";
  catering_notice: string;
  is_open: boolean;
}

interface ResidencyRegistrationItem {
  id: string;
  enrollment: string;
  block: ResidencyBlockItem;
  seat_number: number;
  status: "pending_payment" | "confirmed" | "cancelled";
  status_display: string;
  payment: PaymentInitiateResponse | null;
  dietary_notes: string;
  catering_notice: string;
}

export function MyLearningPage() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [enrollments, setEnrollments] = useState<EnrollmentItem[]>([]);
  const [residencyBlocks, setResidencyBlocks] = useState<ResidencyBlockItem[]>(
    []
  );
  const [residencyRegistrations, setResidencyRegistrations] = useState<
    ResidencyRegistrationItem[]
  >([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [paymentFeedback, setPaymentFeedback] = useState<string | null>(null);
  const [payingEnrollmentId, setPayingEnrollmentId] = useState<string | null>(
    null
  );
  const [bookingBlockId, setBookingBlockId] = useState<string | null>(null);

  const fetchDashboardData = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);

    try {
      const [enrollRes, blocksRes, regsRes] = await Promise.all([
        fetch("/api/enrollments/", {
          method: "GET",
          headers: { Accept: "application/json" },
          credentials: "same-origin",
        }),
        fetch("/api/residency/blocks/", {
          method: "GET",
          headers: { Accept: "application/json" },
          credentials: "same-origin",
        }),
        fetch("/api/residency/registrations/", {
          method: "GET",
          headers: { Accept: "application/json" },
          credentials: "same-origin",
        }),
      ]);

      if (!enrollRes.ok) {
        throw new Error(
          `Failed to load student enrollments (HTTP ${enrollRes.status})`
        );
      }

      const enrollData =
        (await enrollRes.json()) as PaginatedResponse<EnrollmentItem>;
      setEnrollments(enrollData.results ?? []);

      if (blocksRes.ok) {
        const blocksData =
          (await blocksRes.json()) as PaginatedResponse<ResidencyBlockItem>;
        setResidencyBlocks(blocksData.results ?? []);
      }

      if (regsRes.ok) {
        const regsData = (await regsRes.json()) as ResidencyRegistrationItem[];
        setResidencyRegistrations(Array.isArray(regsData) ? regsData : []);
      }
    } catch (err) {
      setErrorMessage(
        err instanceof Error
          ? err.message
          : "Unable to load your learning dashboard."
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchDashboardData();
  }, [fetchDashboardData]);

  const handlePayViaDpo = async (enrollmentId: string) => {
    setPayingEnrollmentId(enrollmentId);
    setPaymentFeedback(null);
    setErrorMessage(null);

    try {
      const csrfToken = await ensureCsrfToken();
      const initRes = await fetch("/api/payments/initiate/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          "X-CSRFToken": csrfToken,
        },
        credentials: "same-origin",
        body: JSON.stringify({ enrollment_id: enrollmentId }),
      });

      const initData: unknown = await initRes.json().catch(() => ({}));
      if (!initRes.ok) {
        throw new Error(
          extractApiErrorMessage(initData, "Unable to initiate DPO payment.")
        );
      }

      const payment = initData as PaymentInitiateResponse;

      if (payment.provider_ref.startsWith("DPO-SANDBOX-")) {
        const verifyRes = await fetch("/api/payments/verify-return/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
            "X-CSRFToken": csrfToken,
          },
          credentials: "same-origin",
          body: JSON.stringify({ provider_ref: payment.provider_ref }),
        });

        const verifyData: unknown = await verifyRes.json().catch(() => ({}));
        if (!verifyRes.ok) {
          throw new Error(
            extractApiErrorMessage(
              verifyData,
              "DPO sandbox verification failed."
            )
          );
        }

        setPaymentFeedback(
          `DPO Pay transaction ${payment.provider_ref} verified server-to-server. Your enrollment is now ACTIVE.`
        );
        await fetchDashboardData();
      } else if (payment.checkout_url) {
        window.location.assign(payment.checkout_url);
      }
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : "Payment initiation failed."
      );
    } finally {
      setPayingEnrollmentId(null);
    }
  };

  const handleBookResidencyBlock = async (blockId: string) => {
    setBookingBlockId(blockId);
    setPaymentFeedback(null);
    setErrorMessage(null);

    try {
      const csrfToken = await ensureCsrfToken();
      const bookRes = await fetch("/api/residency/registrations/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          "X-CSRFToken": csrfToken,
        },
        credentials: "same-origin",
        body: JSON.stringify({
          block_id: blockId,
          dietary_notes: "Standard lunch and tea",
        }),
      });

      const bookData: unknown = await bookRes.json().catch(() => ({}));
      if (!bookRes.ok) {
        throw new Error(
          extractApiErrorMessage(
            bookData,
            "Unable to book 5-day practical residency block."
          )
        );
      }

      const reg = bookData as ResidencyRegistrationItem;
      const providerRef = reg.payment?.provider_ref ?? "";

      if (providerRef.startsWith("DPO-SANDBOX-")) {
        const verifyRes = await fetch("/api/payments/verify-return/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
            "X-CSRFToken": csrfToken,
          },
          credentials: "same-origin",
          body: JSON.stringify({ provider_ref: providerRef }),
        });

        if (verifyRes.ok) {
          setPaymentFeedback(
            `Confirmed Seat #${reg.seat_number} for ${reg.block.location_display} (${reg.block.starts_on} to ${reg.block.ends_on}). $100 USD lunch & tea fee verified.`
          );
        }
        await fetchDashboardData();
      } else if (reg.payment?.checkout_url) {
        window.location.assign(reg.payment.checkout_url);
      }
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : "Residency booking failed."
      );
    } finally {
      setBookingBlockId(null);
    }
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:py-12">
      <header className="border-b border-[var(--color-border-hairline)] pb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="font-clinical-mono text-xs font-semibold uppercase tracking-widest text-[var(--color-accent-terracotta)]">
            Student Learning Dashboard
          </p>
          <h1 className="mt-1 font-editorial text-3xl sm:text-4xl font-semibold text-[var(--color-text-primary)]">
            Welcome, {user?.profile?.display_name || user?.email}
          </h1>
          <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
            Registered Country:{" "}
            <strong className="font-clinical-mono">
              {user?.profile?.country ?? "KE"}
            </strong>{" "}
            · Audience Tier:{" "}
            <strong className="font-clinical-mono uppercase">
              {user?.profile?.effective_audience ?? "local"}
            </strong>{" "}
            · Timezone:{" "}
            <strong className="font-clinical-mono">
              {user?.profile?.timezone ?? "Africa/Nairobi"}
            </strong>
          </p>
        </div>

        <Link
          to="/"
          className="font-clinical-mono text-xs font-semibold uppercase tracking-wider text-[var(--color-accent-terracotta)] underline"
        >
          + Browse More Programmes
        </Link>
      </header>

      {paymentFeedback && (
        <div
          role="status"
          className="mt-6 rounded-[var(--radius-sm)] border border-[var(--color-badge-certificate-border)] bg-[var(--color-status-success-bg)] p-4 text-xs font-medium text-[var(--color-status-success-text)]"
        >
          {paymentFeedback}
        </div>
      )}

      <div className="mt-8">
        {isLoading && (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            <CourseCardSkeleton />
            <CourseCardSkeleton />
          </div>
        )}

        {!isLoading && errorMessage && (
          <ErrorState
            message={errorMessage}
            onRetry={() => {
              void fetchDashboardData();
            }}
          />
        )}

        {!isLoading && !errorMessage && enrollments.length === 0 && (
          <EmptyState
            title="You have no active or pending cohort enrollments yet"
            description="Explore Dr. Violet's Certificate and Diploma programmes in Psychology and select an open intake cohort to enroll."
            actionLabel="Explore Academic Catalog"
            onAction={() => {
              navigate("/");
            }}
          />
        )}

        {!isLoading && !errorMessage && enrollments.length > 0 && (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            {enrollments.map((enrollment) => {
              const isPending = enrollment.status === "pending_payment";
              const isActive =
                enrollment.status === "active" ||
                enrollment.status === "completed";
              const progressValue =
                enrollment.status === "completed" ? 100 : isActive ? 10 : 0;
              const progressLabel = isPending
                ? "Awaiting DPO Tuition Verification"
                : "Lesson & Live Lecture Progress";

              const courseBlocks = residencyBlocks.filter(
                (b) => b.course === enrollment.course.id
              );
              const existingReg = residencyRegistrations.find(
                (r) =>
                  r.enrollment === enrollment.id && r.status !== "cancelled"
              );

              return (
                <Card
                  key={enrollment.id}
                  specLabel={`COHORT // ${enrollment.cohort.name.toUpperCase()}`}
                  specCode={`STATUS: ${enrollment.status.toUpperCase()}`}
                >
                  <div className="p-5 sm:p-6 flex-1 flex flex-col justify-between space-y-5">
                    <div>
                      <div className="flex flex-wrap items-center gap-2 mb-3">
                        <Badge level={enrollment.course.level}>
                          {enrollment.course.level_display}
                        </Badge>
                        <Badge residency={enrollment.course.residency}>
                          {enrollment.course.residency_display}
                        </Badge>
                      </div>

                      <h2 className="font-editorial text-2xl font-semibold text-[var(--color-text-primary)]">
                        <Link
                          to={`/courses/${enrollment.course.slug}`}
                          className="hover:text-[var(--color-accent-terracotta)]"
                        >
                          {enrollment.course.title}
                        </Link>
                      </h2>

                      <p className="mt-2 text-xs text-[var(--color-text-secondary)]">
                        Cohort Starts:{" "}
                        <strong className="font-clinical-mono">
                          {enrollment.cohort.starts_on}
                        </strong>
                      </p>

                      <div className="mt-4">
                        <ProgressBar
                          value={progressValue}
                          label={progressLabel}
                        />
                      </div>

                      {/* Phase 5: 5-Day Nairobi & Embu Practical Residency Booking Section */}
                      {isActive &&
                        enrollment.course.residency !== "none" && (
                          <div className="mt-4 rounded-[var(--radius-sm)] border border-[var(--color-accent-terracotta-border)] bg-[var(--color-accent-terracotta-bg)] p-3.5 text-xs space-y-2">
                            <p className="font-clinical-mono font-semibold uppercase text-[var(--color-accent-terracotta)]">
                              5-Day Practical Block (Nairobi / Embu) · $100 USD
                            </p>
                            <p className="text-[var(--color-text-secondary)]">
                              Fee covers daily lunch and teas. Travel and lodging are the
                              student&apos;s responsibility.
                            </p>

                            {existingReg ? (
                              <p className="font-clinical-mono font-semibold text-[var(--color-status-success-text)]">
                                ✓ Booked: {existingReg.block.location_display} (
                                {existingReg.block.starts_on} to{" "}
                                {existingReg.block.ends_on}) · Seat #
                                {existingReg.seat_number} [
                                {existingReg.status.toUpperCase()}]
                              </p>
                            ) : (
                              <div className="flex flex-wrap gap-2 pt-1">
                                {courseBlocks.map((block) => (
                                  <Button
                                    key={block.id}
                                    size="sm"
                                    variant="secondary"
                                    disabled={block.seats_remaining <= 0}
                                    isLoading={bookingBlockId === block.id}
                                    onClick={() => {
                                      void handleBookResidencyBlock(block.id);
                                    }}
                                  >
                                    Book {block.location_display} (
                                    {block.starts_on} · {block.seats_remaining}{" "}
                                    seats left)
                                  </Button>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                    </div>

                    <div className="border-t border-[var(--color-border-hairline)] pt-4 flex flex-wrap items-center justify-between gap-4">
                      <div>
                        <span className="block font-clinical-mono text-[11px] uppercase text-[var(--color-text-muted)]">
                          Server-Verified Tuition
                        </span>
                        <span className="font-clinical-mono text-lg font-semibold text-[var(--color-text-primary)]">
                          {enrollment.expected_price
                            ? formatMinorCurrency(
                                enrollment.expected_price.amount_minor,
                                enrollment.expected_price.currency
                              )
                            : "Assigned by Staff"}
                        </span>
                      </div>

                      {isPending ? (
                        <Button
                          size="sm"
                          isLoading={payingEnrollmentId === enrollment.id}
                          onClick={() => {
                            void handlePayViaDpo(enrollment.id);
                          }}
                        >
                          Pay via DPO Link →
                        </Button>
                      ) : (
                        <Button
                          size="sm"
                          onClick={() => {
                            navigate(`/classroom/${enrollment.course.slug}`);
                          }}
                        >
                          Enter Classroom →
                        </Button>
                      )}
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}